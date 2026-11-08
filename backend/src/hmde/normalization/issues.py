"""Normalization issue and review audit helpers."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import NormalizationIssue, NormalizationIssueAction


def issue_key(
    *,
    dataset_version: str,
    taxonomy_version: str,
    entity_type: str,
    entity_mbid: str | None,
    issue_type: str,
    reason: str,
) -> str:
    payload = "|".join(
        (
            dataset_version,
            taxonomy_version,
            entity_type,
            entity_mbid or "",
            issue_type,
            reason,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_issue(
    session: Session,
    *,
    run_id: uuid.UUID,
    dataset_version: str,
    taxonomy_version: str | None,
    entity_type: str,
    entity_mbid: str | None,
    issue_type: str,
    severity: str,
    reason: str,
    evidence: dict[str, Any] | None = None,
) -> NormalizationIssue:
    key = issue_key(
        dataset_version=dataset_version,
        taxonomy_version=taxonomy_version or "",
        entity_type=entity_type,
        entity_mbid=entity_mbid,
        issue_type=issue_type,
        reason=reason,
    )
    existing = session.scalar(select(NormalizationIssue).where(NormalizationIssue.issue_key == key))
    values = {
        "normalization_run_id": run_id,
        "entity_type": entity_type,
        "entity_mbid": entity_mbid,
        "taxonomy_version": taxonomy_version,
        "issue_type": issue_type,
        "severity": severity,
        "reason": reason,
        "evidence": evidence or {},
        "updated_at": datetime.now(UTC),
    }
    if existing is None:
        existing = NormalizationIssue(
            id=uuid.uuid4(),
            issue_key=key,
            status="open",
            **values,
        )
        session.add(existing)
    else:
        for name, value in values.items():
            setattr(existing, name, value)
    session.flush()
    return existing


def record_issue_action(
    session: Session,
    *,
    issue: NormalizationIssue,
    action: str,
    actor: str,
    source_file: str | None = None,
    previous_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> NormalizationIssueAction:
    row = NormalizationIssueAction(
        id=uuid.uuid4(),
        issue_id=issue.id,
        action=action,
        actor=actor,
        source_file=source_file,
        previous_value=previous_value,
        new_value=new_value,
    )
    session.add(row)
    session.flush()
    return row


def serialize_issue(issue: NormalizationIssue) -> dict[str, Any]:
    return {
        "issue_key": issue.issue_key,
        "entity_type": issue.entity_type,
        "entity_mbid": issue.entity_mbid,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "status": issue.status,
        "reason": issue.reason,
        "evidence": issue.evidence,
    }


def issues_json(issues: list[NormalizationIssue]) -> str:
    return json.dumps([serialize_issue(issue) for issue in issues], sort_keys=True)
