"""Quality exception baseline loading and gate evaluation."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import QualityException, QualityFinding, QualityRule

from .catalogue import RuleCatalogue
from .errors import QualityError, QualityInputError


@dataclass(frozen=True, slots=True)
class ExceptionDefinition:
    rule_code: str
    entity_type: str
    entity_mbid: str | None
    reason: str
    approved_by: str
    approved_at: date


@dataclass(frozen=True, slots=True)
class ExceptionBaseline:
    version: str
    catalogue_version: str
    exceptions: tuple[ExceptionDefinition, ...]


@dataclass(frozen=True, slots=True)
class GateResult:
    blocking_unexcepted: int
    blocking_excepted: int
    advisory: int
    status: str


def load_exception_baseline(path: Path, catalogue: RuleCatalogue) -> ExceptionBaseline:
    if not path.is_file():
        raise QualityInputError(f"quality exception baseline does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityInputError(f"could not read quality exception baseline: {path}") from exc
    if not isinstance(payload, dict):
        raise QualityInputError("quality exception baseline root must be an object")
    version = _required(payload, "version")
    catalogue_version = _required(payload, "catalogue_version")
    if catalogue_version != catalogue.version:
        raise QualityInputError("exception baseline catalogue version mismatch")
    raw_exceptions = payload.get("exceptions")
    if not isinstance(raw_exceptions, list):
        raise QualityInputError("exception baseline must contain an exceptions array")
    known_rules = catalogue.by_code()
    exceptions: list[ExceptionDefinition] = []
    seen: set[tuple[str, str, str | None]] = set()
    for index, raw in enumerate(raw_exceptions, start=1):
        if not isinstance(raw, dict):
            raise QualityInputError(f"exception at position {index} must be an object")
        rule_code = _required(raw, "rule_code", position=index)
        if rule_code not in known_rules:
            raise QualityInputError(f"exception references unknown rule: {rule_code}")
        entity_type = _required(raw, "entity_type", position=index)
        entity_mbid = _optional(raw.get("entity_mbid"))
        key = (rule_code, entity_type, entity_mbid)
        if key in seen:
            raise QualityInputError(f"duplicate quality exception: {key}")
        reason = _required(raw, "reason", position=index)
        approved_by = _required(raw, "approved_by", position=index)
        approved_at_text = _required(raw, "approved_at", position=index)
        try:
            approved_at = date.fromisoformat(approved_at_text)
        except ValueError as exc:
            raise QualityInputError(
                f"exception at position {index} has an invalid approved_at"
            ) from exc
        seen.add(key)
        exceptions.append(
            ExceptionDefinition(
                rule_code=rule_code,
                entity_type=entity_type,
                entity_mbid=entity_mbid,
                reason=reason,
                approved_by=approved_by,
                approved_at=approved_at,
            )
        )
    return ExceptionBaseline(
        version=version,
        catalogue_version=catalogue_version,
        exceptions=tuple(exceptions),
    )


def sync_exceptions(
    session: Session,
    *,
    baseline: ExceptionBaseline,
    rules: dict[str, QualityRule],
) -> dict[tuple[str, str, str | None], QualityException]:
    result: dict[tuple[str, str, str | None], QualityException] = {}
    for definition in baseline.exceptions:
        rule = rules.get(definition.rule_code)
        if rule is None:
            raise QualityError(f"missing rule for exception: {definition.rule_code}")
        key = exception_key(
            catalogue_version=baseline.catalogue_version,
            rule_code=definition.rule_code,
            entity_type=definition.entity_type,
            entity_mbid=definition.entity_mbid,
        )
        row = session.scalar(select(QualityException).where(QualityException.exception_key == key))
        values = {
            "catalogue_version": baseline.catalogue_version,
            "rule_id": rule.id,
            "entity_type": definition.entity_type,
            "entity_mbid": definition.entity_mbid,
            "status": "active",
            "reason": definition.reason,
            "approved_by": definition.approved_by,
            "approved_at": definition.approved_at,
        }
        if row is None:
            row = QualityException(id=uuid.uuid4(), exception_key=key, **values)
            session.add(row)
        else:
            for name, value in values.items():
                setattr(row, name, value)
        result[(definition.rule_code, definition.entity_type, definition.entity_mbid)] = row
    session.flush()
    return result


def evaluate_gate(
    findings: list[QualityFinding],
    *,
    rules: dict[str, QualityRule],
    exceptions: dict[tuple[str, str, str | None], QualityException],
    strict: bool,
) -> GateResult:
    rule_by_id = {rule.id: rule for rule in rules.values()}
    blocking_unexcepted = blocking_excepted = advisory = 0
    for finding in findings:
        rule = rule_by_id.get(finding.rule_id)
        if rule is None:
            raise QualityError(f"finding references unknown rule id: {finding.rule_id}")
        exception = exceptions.get((rule.code, finding.entity_type, finding.entity_mbid))
        if exception is not None:
            if finding.severity == "blocking":
                blocking_excepted += 1
            else:
                advisory += 1
            finding.status = "exceptional"
        elif finding.severity == "blocking":
            blocking_unexcepted += 1
            finding.status = "open"
        else:
            advisory += 1
            finding.status = "open"
    status = (
        "blocked"
        if strict and blocking_unexcepted
        else ("completed_with_findings" if findings else "completed")
    )
    return GateResult(
        blocking_unexcepted=blocking_unexcepted,
        blocking_excepted=blocking_excepted,
        advisory=advisory,
        status=status,
    )


def exception_key(
    *,
    catalogue_version: str,
    rule_code: str,
    entity_type: str,
    entity_mbid: str | None,
) -> str:
    payload = "|".join((catalogue_version, rule_code, entity_type, entity_mbid or ""))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required(payload: dict[str, Any], key: str, *, position: int | None = None) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        location = f"exception at position {position}" if position else "exception baseline"
        raise QualityInputError(f"{location} is missing a valid {key}")
    return value.strip()


def _optional(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
