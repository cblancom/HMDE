"""Hybrid exact-label album classification."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from hmde.models import ReleaseGroupSubgenre

from .entities import EntityIndex, read_ndjson
from .errors import InputValidationError
from .inputs import ManualOverride, NormalizationInputs, TagMapRule
from .issues import record_issue

HIGH_CONFIDENCE = 0.80
MEDIUM_CONFIDENCE = 0.50


@dataclass(frozen=True, slots=True)
class Candidate:
    code: str
    confidence: float
    priority: int
    labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClassificationCounts:
    release_groups: int
    accepted: int
    review: int
    quarantined: int
    overrides_applied: int
    primary_labels: int
    secondary_labels: int


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    counts: ClassificationCounts
    issues: tuple[Any, ...]


def classify_albums(
    session: Session,
    inputs: NormalizationInputs,
    index: EntityIndex,
    *,
    run_id: uuid.UUID,
) -> ClassificationResult:
    rows = read_ndjson(inputs.dataset.file("release_groups.ndjson").path)
    overrides = {item.release_group_mbid: item for item in inputs.overrides.overrides}
    rules = {rule.source_label: rule for rule in inputs.tag_map.rules}
    issues: list[Any] = []
    accepted = review = quarantined = overrides_applied = 0
    primary_labels = secondary_labels = 0

    for row in rows:
        mbid = _required(row, "mbid")
        release_group_id = index.release_groups.get(mbid)
        if release_group_id is None:
            raise InputValidationError(f"release group is not normalized: {mbid}")
        override = overrides.get(mbid)
        if override is not None:
            accepted_codes = _override_codes(override)
            status = "accepted"
            primary = override.primary_code
            confidence = 1.0
            mapping_rule = "override"
            evidence = {
                "source": "manual-override",
                "override_version": inputs.overrides.version,
                "reason": override.reason,
                "reviewer": override.reviewer,
                "reviewed_at": override.reviewed_at,
            }
            overrides_applied += 1
            accepted += 1
        else:
            candidates = _candidates(row, rules)
            if not candidates:
                quarantined += 1
                issues.append(
                    record_issue(
                        session,
                        run_id=run_id,
                        dataset_version=inputs.dataset.dataset_version,
                        taxonomy_version=inputs.dataset.taxonomy_version,
                        entity_type="release_group",
                        entity_mbid=mbid,
                        issue_type="classification_missing",
                        severity="blocking",
                        reason="no exact tag/genre mapping",
                        evidence={"genres": row.get("genres", []), "tags": row.get("tags", [])},
                    )
                )
                _clear_classifications(session, release_group_id, inputs.dataset.taxonomy_version)
                continue
            primary, confidence, candidates, conflict = _choose_primary(candidates)
            if conflict:
                quarantined += 1
                issues.append(
                    record_issue(
                        session,
                        run_id=run_id,
                        dataset_version=inputs.dataset.dataset_version,
                        taxonomy_version=inputs.dataset.taxonomy_version,
                        entity_type="release_group",
                        entity_mbid=mbid,
                        issue_type="classification_conflict",
                        severity="blocking",
                        reason="multiple equally ranked primary candidates",
                        evidence={
                            "candidates": [
                                {
                                    "code": item.code,
                                    "confidence": item.confidence,
                                    "priority": item.priority,
                                    "labels": list(item.labels),
                                }
                                for item in candidates
                            ]
                        },
                    )
                )
                _clear_classifications(session, release_group_id, inputs.dataset.taxonomy_version)
                continue
            if confidence < MEDIUM_CONFIDENCE:
                quarantined += 1
                issues.append(
                    record_issue(
                        session,
                        run_id=run_id,
                        dataset_version=inputs.dataset.dataset_version,
                        taxonomy_version=inputs.dataset.taxonomy_version,
                        entity_type="release_group",
                        entity_mbid=mbid,
                        issue_type="classification_low_confidence",
                        severity="blocking",
                        reason="best exact mapping is below the medium threshold",
                        evidence={"primary": primary.code, "confidence": confidence},
                    )
                )
                _clear_classifications(session, release_group_id, inputs.dataset.taxonomy_version)
                continue
            accepted_codes = [primary.code] + [
                item.code
                for item in candidates
                if item.code != primary.code and item.confidence >= MEDIUM_CONFIDENCE
            ]
            if confidence < HIGH_CONFIDENCE:
                review += 1
                status = "review"
                issues.append(
                    record_issue(
                        session,
                        run_id=run_id,
                        dataset_version=inputs.dataset.dataset_version,
                        taxonomy_version=inputs.dataset.taxonomy_version,
                        entity_type="release_group",
                        entity_mbid=mbid,
                        issue_type="classification_review",
                        severity="medium",
                        reason="mapping confidence is in the review band",
                        evidence={"primary": primary.code, "confidence": confidence},
                    )
                )
            else:
                accepted += 1
                status = "accepted"
            mapping_rule = "tag-exact"
            evidence = {
                "source": "tag-map",
                "tag_map_version": inputs.tag_map.version,
                "primary_confidence": confidence,
                "candidates": [
                    {
                        "code": item.code,
                        "confidence": item.confidence,
                        "priority": item.priority,
                        "labels": list(item.labels),
                    }
                    for item in candidates
                ],
            }
        _replace_classifications(
            session,
            release_group_id=release_group_id,
            taxonomy_version=inputs.dataset.taxonomy_version,
            primary_code=primary if isinstance(primary, str) else primary.code,
            codes=accepted_codes,
            confidence=confidence,
            status=status,
            mapping_rule=mapping_rule,
            source_record_id=_source_id(row, index),
            evidence=evidence,
        )
        primary_labels += 1
        secondary_labels += max(0, len(accepted_codes) - 1)

    session.flush()
    return ClassificationResult(
        counts=ClassificationCounts(
            release_groups=len(rows),
            accepted=accepted,
            review=review,
            quarantined=quarantined,
            overrides_applied=overrides_applied,
            primary_labels=primary_labels,
            secondary_labels=secondary_labels,
        ),
        issues=tuple(issues),
    )


def _candidates(row: dict[str, Any], rules: dict[str, TagMapRule]) -> list[Candidate]:
    labels = sorted(
        {
            str(value).strip().casefold()
            for field in ("genres", "tags")
            for value in row.get(field, [])
            if isinstance(value, str) and value.strip()
        }
    )
    by_code: dict[str, Candidate] = {}
    for label in labels:
        rule = rules.get(label)
        if rule is None:
            continue
        current = by_code.get(rule.target_code)
        if current is None:
            by_code[rule.target_code] = Candidate(
                code=rule.target_code,
                confidence=rule.confidence,
                priority=rule.priority,
                labels=(label,),
            )
        else:
            better = rule.confidence > current.confidence or (
                rule.confidence == current.confidence and rule.priority < current.priority
            )
            by_code[rule.target_code] = Candidate(
                code=current.code,
                confidence=max(current.confidence, rule.confidence),
                priority=min(current.priority, rule.priority) if better else current.priority,
                labels=tuple(sorted(set(current.labels + (label,)))),
            )
    return sorted(by_code.values(), key=lambda item: (-item.confidence, item.priority, item.code))


def _choose_primary(candidates: list[Candidate]) -> tuple[Candidate, float, list[Candidate], bool]:
    top = candidates[0]
    tied = [
        item
        for item in candidates
        if item.confidence == top.confidence and item.priority == top.priority
    ]
    conflict = len(tied) > 1
    return top, top.confidence, candidates, conflict


def _override_codes(override: ManualOverride) -> list[str]:
    return [override.primary_code, *override.secondary_codes]


def _replace_classifications(
    session: Session,
    *,
    release_group_id: uuid.UUID,
    taxonomy_version: str,
    primary_code: str,
    codes: list[str],
    confidence: float,
    status: str,
    mapping_rule: str,
    source_record_id: uuid.UUID,
    evidence: dict[str, Any],
) -> None:
    existing = {
        row.subgenre_code: row
        for row in session.scalars(
            select(ReleaseGroupSubgenre).where(
                ReleaseGroupSubgenre.release_group_id == release_group_id,
                ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
            )
        )
    }
    desired = set(codes)
    stale = set(existing) - desired
    if stale:
        session.execute(
            delete(ReleaseGroupSubgenre).where(
                ReleaseGroupSubgenre.release_group_id == release_group_id,
                ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
                ReleaseGroupSubgenre.subgenre_code.in_(stale),
            )
        )
        session.flush()
    for code in sorted(desired):
        row = existing.get(code)
        is_primary = code == primary_code
        if row is None:
            session.add(
                ReleaseGroupSubgenre(
                    release_group_id=release_group_id,
                    taxonomy_version=taxonomy_version,
                    subgenre_code=code,
                    is_primary=is_primary,
                    confidence=confidence,
                    status=status,
                    mapping_rule=mapping_rule,
                    source_record_id=source_record_id,
                    evidence=evidence,
                )
            )
        else:
            row.is_primary = is_primary
            row.confidence = confidence
            row.status = status
            row.mapping_rule = mapping_rule
            row.source_record_id = source_record_id
            row.evidence = evidence


def _clear_classifications(
    session: Session,
    release_group_id: uuid.UUID,
    taxonomy_version: str,
) -> None:
    session.execute(
        delete(ReleaseGroupSubgenre).where(
            ReleaseGroupSubgenre.release_group_id == release_group_id,
            ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
        )
    )


def _source_id(row: dict[str, Any], index: EntityIndex) -> uuid.UUID:
    raw_id = row.get("raw_response_id")
    if not isinstance(raw_id, str):
        raise InputValidationError("release group is missing raw_response_id")
    try:
        source_id = index.source_records.get(uuid.UUID(raw_id))
    except ValueError as exc:
        raise InputValidationError("release group has an invalid raw_response_id") from exc
    if source_id is None:
        raise InputValidationError("release group is missing source provenance")
    return source_id


def _required(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"record is missing a valid {key}")
    return value.strip()
