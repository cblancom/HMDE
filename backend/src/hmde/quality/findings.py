"""Quality finding specification and persistence."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import QualityFinding, QualityRule, QualityRun


@dataclass(frozen=True, slots=True)
class FindingSpec:
    rule_code: str
    entity_type: str
    entity_mbid: str | None
    entity_id: uuid.UUID | None
    observed_value: dict[str, Any]
    expected_value: dict[str, Any]
    details: dict[str, Any]


def finding_key(
    *,
    run_id: uuid.UUID,
    rule_code: str,
    entity_type: str,
    entity_mbid: str | None,
    entity_id: uuid.UUID | None,
    observed_value: dict[str, Any],
) -> str:
    payload = "|".join(
        (
            str(run_id),
            rule_code,
            entity_type,
            entity_mbid or "",
            str(entity_id or ""),
            json.dumps(observed_value, sort_keys=True, separators=(",", ":")),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def persist_findings(
    session: Session,
    *,
    run: QualityRun,
    rules: dict[str, QualityRule],
    specs: list[FindingSpec],
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for spec in specs:
        rule = rules.get(spec.rule_code)
        if rule is None:
            raise ValueError(f"quality finding references unknown rule: {spec.rule_code}")
        key = finding_key(
            run_id=run.id,
            rule_code=spec.rule_code,
            entity_type=spec.entity_type,
            entity_mbid=spec.entity_mbid,
            entity_id=spec.entity_id,
            observed_value=spec.observed_value,
        )
        row = session.scalar(
            select(QualityFinding).where(
                QualityFinding.quality_run_id == run.id,
                QualityFinding.finding_key == key,
            )
        )
        values = {
            "rule_id": rule.id,
            "entity_type": spec.entity_type,
            "entity_mbid": spec.entity_mbid,
            "entity_id": spec.entity_id,
            "severity": rule.severity,
            "observed_value": spec.observed_value,
            "expected_value": spec.expected_value,
            "details": spec.details,
            "updated_at": datetime.now(UTC),
        }
        if row is None:
            row = QualityFinding(
                id=uuid.uuid4(),
                quality_run_id=run.id,
                finding_key=key,
                status="open",
                **values,
            )
            session.add(row)
        else:
            for name, value in values.items():
                setattr(row, name, value)
        findings.append(row)
    session.flush()
    return findings


def findings_json(findings: list[QualityFinding]) -> str:
    return json.dumps(
        [
            {
                "finding_key": finding.finding_key,
                "entity_type": finding.entity_type,
                "entity_mbid": finding.entity_mbid,
                "severity": finding.severity,
                "status": finding.status,
                "observed_value": finding.observed_value,
                "expected_value": finding.expected_value,
                "details": finding.details,
            }
            for finding in findings
        ],
        sort_keys=True,
    )
