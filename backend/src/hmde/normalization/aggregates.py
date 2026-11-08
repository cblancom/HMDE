"""Band aggregate derivation and current projection refresh."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from hmde.models import (
    Artist,
    ArtistSubgenre,
    ArtistSubgenreClassification,
    ReleaseGroup,
    ReleaseGroupSubgenre,
)

from .entities import EntityIndex, read_ndjson
from .errors import InputValidationError
from .inputs import NormalizationInputs
from .issues import record_issue

ACCEPTED_CONFIDENCE = 0.80
REVIEW_CONFIDENCE = 0.50


@dataclass(frozen=True, slots=True)
class AggregateDecision:
    code: str | None
    confidence: float
    status: str
    mapping_rule: str
    issue_type: str | None
    severity: str | None
    reason: str | None
    evidence: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AggregateCounts:
    bands: int
    accepted: int
    review: int
    missing: int
    fallback: int


@dataclass(frozen=True, slots=True)
class AggregateResult:
    counts: AggregateCounts
    issues: tuple[Any, ...]


def choose_aggregate(
    counts: Counter[str],
    *,
    seed_code: str | None,
) -> AggregateDecision:
    total = sum(counts.values())
    if not counts:
        if seed_code is None:
            return AggregateDecision(
                code=None,
                confidence=0.0,
                status="quarantined",
                mapping_rule="missing",
                issue_type="aggregate_missing",
                severity="blocking",
                reason="no classified albums and no seed-list leaf",
                evidence={"counts": {}, "seed_code": None},
            )
        return AggregateDecision(
            code=seed_code,
            confidence=REVIEW_CONFIDENCE,
            status="review",
            mapping_rule="seed-fallback",
            issue_type="aggregate_fallback",
            severity="medium",
            reason="no classified albums; using approved seed-list leaf",
            evidence={"counts": {}, "seed_code": seed_code},
        )

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_code, top_count = ranked[0]
    tied = [code for code, count in ranked if count == top_count]
    if len(tied) > 1:
        code = seed_code if seed_code in tied else seed_code or tied[0]
        if seed_code is None:
            return AggregateDecision(
                code=None,
                confidence=0.0,
                status="quarantined",
                mapping_rule="missing",
                issue_type="aggregate_tie",
                severity="blocking",
                reason="band aggregate is tied and no seed-list leaf is available",
                evidence={"counts": dict(counts), "tied": tied, "seed_code": None},
            )
        return AggregateDecision(
            code=code,
            confidence=REVIEW_CONFIDENCE,
            status="review",
            mapping_rule="seed-tiebreak",
            issue_type="aggregate_tie",
            severity="medium",
            reason="band aggregate is tied; using approved seed-list leaf",
            evidence={"counts": dict(counts), "tied": tied, "seed_code": seed_code},
        )

    confidence = top_count / total
    if confidence < REVIEW_CONFIDENCE:
        if seed_code is not None:
            return AggregateDecision(
                code=seed_code,
                confidence=confidence,
                status="review",
                mapping_rule="seed-low-confidence",
                issue_type="aggregate_low_confidence",
                severity="medium",
                reason="low-confidence album plurality; using approved seed-list leaf",
                evidence={
                    "counts": dict(counts),
                    "tied": [top_code],
                    "seed_code": seed_code,
                },
            )
        status = "quarantined"
        issue_type = "aggregate_low_confidence"
        severity = "blocking"
        reason = "band aggregate confidence is below the review threshold"
    elif confidence < ACCEPTED_CONFIDENCE:
        status = "review"
        issue_type = "aggregate_review"
        severity = "medium"
        reason = "band aggregate confidence is in the review band"
    else:
        status = "accepted"
        issue_type = severity = reason = None
    return AggregateDecision(
        code=top_code,
        confidence=confidence,
        status=status,
        mapping_rule="album-majority",
        issue_type=issue_type,
        severity=severity,
        reason=reason,
        evidence={"counts": dict(counts), "tied": [top_code], "seed_code": seed_code},
    )


def derive_band_aggregates(
    session: Session,
    inputs: NormalizationInputs,
    index: EntityIndex,
    *,
    run_id: uuid.UUID,
    seed_subgenres: dict[str, str] | None = None,
) -> AggregateResult:
    seed_subgenres = seed_subgenres or {}
    rows = read_ndjson(inputs.dataset.file("artists.ndjson").path)
    issues: list[Any] = []
    accepted = review = missing = fallback = 0

    for row in rows:
        mbid = _required(row, "mbid")
        artist_id = index.artists.get(mbid)
        if artist_id is None:
            raise InputValidationError(f"seed band is not normalized: {mbid}")
        classes = session.scalars(
            select(ReleaseGroupSubgenre)
            .join(ReleaseGroup, ReleaseGroup.id == ReleaseGroupSubgenre.release_group_id)
            .where(
                ReleaseGroup.artist_id == artist_id,
                ReleaseGroupSubgenre.taxonomy_version == inputs.dataset.taxonomy_version,
                ReleaseGroupSubgenre.is_primary.is_(True),
            )
            .order_by(ReleaseGroupSubgenre.release_group_id)
        ).all()
        counts: Counter[str] = Counter(item.subgenre_code for item in classes)
        seed_code = seed_subgenres.get(mbid)
        decision = choose_aggregate(counts, seed_code=seed_code)
        if decision.code is None:
            missing += 1
        elif decision.status == "accepted":
            accepted += 1
        else:
            review += 1
            if decision.mapping_rule == "seed-fallback":
                fallback += 1
        if decision.issue_type is not None:
            issues.append(
                record_issue(
                    session,
                    run_id=run_id,
                    dataset_version=inputs.dataset.dataset_version,
                    taxonomy_version=inputs.dataset.taxonomy_version,
                    entity_type="artist",
                    entity_mbid=mbid,
                    issue_type=decision.issue_type,
                    severity=decision.severity or "medium",
                    reason=decision.reason or decision.issue_type,
                    evidence=decision.evidence,
                )
            )
        if decision.code is None:
            _clear_current_projection(session, artist_id)
            continue

        source_record_id = _aggregate_source(
            session,
            classes=classes,
            artist_id=artist_id,
        )
        _persist_aggregate(
            session,
            artist_id=artist_id,
            mbid=mbid,
            code=decision.code,
            taxonomy_version=inputs.dataset.taxonomy_version,
            confidence=decision.confidence,
            status=decision.status,
            mapping_rule=decision.mapping_rule,
            source_record_id=source_record_id,
            evidence=decision.evidence,
        )

    session.flush()
    return AggregateResult(
        counts=AggregateCounts(
            bands=len(rows),
            accepted=accepted,
            review=review,
            missing=missing,
            fallback=fallback,
        ),
        issues=tuple(issues),
    )


def _aggregate_source(
    session: Session,
    *,
    classes: list[ReleaseGroupSubgenre],
    artist_id: uuid.UUID,
) -> uuid.UUID:
    if classes:
        return classes[0].source_record_id
    artist = session.get(Artist, artist_id)
    if artist is None:
        raise InputValidationError(f"artist disappeared during aggregation: {artist_id}")
    return artist.source_record_id


def _persist_aggregate(
    session: Session,
    *,
    artist_id: uuid.UUID,
    mbid: str,
    code: str,
    taxonomy_version: str,
    confidence: float,
    status: str,
    mapping_rule: str,
    source_record_id: uuid.UUID,
    evidence: dict[str, Any],
) -> None:
    session.execute(
        delete(ArtistSubgenreClassification).where(
            ArtistSubgenreClassification.artist_id == artist_id,
            ArtistSubgenreClassification.taxonomy_version == taxonomy_version,
        )
    )
    session.flush()
    session.add(
        ArtistSubgenreClassification(
            artist_id=artist_id,
            taxonomy_version=taxonomy_version,
            subgenre_code=code,
            is_primary=True,
            confidence=confidence,
            status=status,
            mapping_rule=mapping_rule,
            source_record_id=source_record_id,
            evidence=evidence,
        )
    )
    session.execute(delete(ArtistSubgenre).where(ArtistSubgenre.artist_id == artist_id))
    session.flush()
    session.add(
        ArtistSubgenre(
            artist_id=artist_id,
            subgenre_code=code,
            is_primary=True,
            confidence=confidence,
            source_record_id=source_record_id,
            taxonomy_version=taxonomy_version,
            status=status,
            mapping_rule=mapping_rule,
        )
    )
    session.flush()


def _clear_current_projection(session: Session, artist_id: uuid.UUID) -> None:
    session.execute(delete(ArtistSubgenre).where(ArtistSubgenre.artist_id == artist_id))
    session.flush()


def _required(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"record is missing a valid {key}")
    return value.strip()
