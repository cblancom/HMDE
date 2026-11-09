"""Versioned quality rule catalogue loading and synchronization."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from hmde.models import QualityRule, QualityRuleCatalogue

from .errors import QualityCatalogueError

DIMENSIONS = {"structural", "completeness", "validity", "consistency", "coverage"}
SEVERITIES = {"blocking", "high", "medium", "info"}
RULE_NAMESPACE = uuid.NAMESPACE_URL


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    code: str
    name: str
    dimension: str
    severity: str
    entity_scope: str
    description: str
    expected: str
    threshold: float | None
    remediation: str
    display_order: int


@dataclass(frozen=True, slots=True)
class RuleCatalogue:
    version: str
    schema_version: int
    source_hash: str
    source_path: str
    rules: tuple[RuleDefinition, ...]

    def by_code(self) -> dict[str, RuleDefinition]:
        return {rule.code: rule for rule in self.rules}


def load_rule_catalogue(path: Path) -> RuleCatalogue:
    if not path.is_file():
        raise QualityCatalogueError(f"quality rule catalogue does not exist: {path}")
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualityCatalogueError(f"could not read quality rule catalogue: {path}") from exc
    if not isinstance(payload, dict):
        raise QualityCatalogueError("quality rule catalogue root must be an object")
    version = _required(payload, "version")
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int) or schema_version < 1:
        raise QualityCatalogueError("quality rule catalogue schema_version must be positive")
    raw_rules = payload.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise QualityCatalogueError("quality rule catalogue must contain rules")
    rules: list[RuleDefinition] = []
    seen: set[str] = set()
    for index, raw_rule in enumerate(raw_rules, start=1):
        if not isinstance(raw_rule, dict):
            raise QualityCatalogueError(f"rule at position {index} must be an object")
        code = _required(raw_rule, "code", position=index)
        if code in seen:
            raise QualityCatalogueError(f"duplicate quality rule code: {code}")
        dimension = _required(raw_rule, "dimension", position=index)
        severity = _required(raw_rule, "severity", position=index)
        if dimension not in DIMENSIONS:
            raise QualityCatalogueError(f"rule {code} has invalid dimension {dimension!r}")
        if severity not in SEVERITIES:
            raise QualityCatalogueError(f"rule {code} has invalid severity {severity!r}")
        threshold = raw_rule.get("threshold")
        if threshold is not None and not isinstance(threshold, (int, float)):
            raise QualityCatalogueError(f"rule {code} has invalid threshold")
        seen.add(code)
        rules.append(
            RuleDefinition(
                code=code,
                name=_required(raw_rule, "name", position=index),
                dimension=dimension,
                severity=severity,
                entity_scope=_required(raw_rule, "entity_scope", position=index),
                description=_required(raw_rule, "description", position=index),
                expected=_required(raw_rule, "expected", position=index),
                threshold=float(threshold) if threshold is not None else None,
                remediation=_required(raw_rule, "remediation", position=index),
                display_order=index,
            )
        )
    return RuleCatalogue(
        version=version,
        schema_version=schema_version,
        source_hash=hashlib.sha256(raw).hexdigest(),
        source_path=str(path),
        rules=tuple(rules),
    )


def sync_catalogue(session: Session, catalogue: RuleCatalogue) -> dict[str, QualityRule]:
    existing = session.get(QualityRuleCatalogue, catalogue.version)
    if existing is None:
        existing = QualityRuleCatalogue(
            version=catalogue.version,
            schema_version=catalogue.schema_version,
            source_hash=catalogue.source_hash,
            source_path=catalogue.source_path,
        )
        session.add(existing)
        session.flush()
    elif existing.source_hash != catalogue.source_hash:
        raise QualityCatalogueError(
            f"quality catalogue {catalogue.version!r} already exists with different content"
        )

    rules: dict[str, QualityRule] = {}
    for definition in catalogue.rules:
        rule_id = uuid.uuid5(
            RULE_NAMESPACE,
            f"hmde-quality-rule:{catalogue.version}:{definition.code}",
        )
        row = session.get(QualityRule, rule_id)
        if row is None:
            row = QualityRule(
                id=rule_id,
                catalogue_version=catalogue.version,
                code=definition.code,
                name=definition.name,
                dimension=definition.dimension,
                severity=definition.severity,
                entity_scope=definition.entity_scope,
                description=definition.description,
                expected=definition.expected,
                threshold=definition.threshold,
                remediation=definition.remediation,
                display_order=definition.display_order,
            )
            session.add(row)
        else:
            row.name = definition.name
            row.dimension = definition.dimension
            row.severity = definition.severity
            row.entity_scope = definition.entity_scope
            row.description = definition.description
            row.expected = definition.expected
            row.threshold = definition.threshold
            row.remediation = definition.remediation
            row.display_order = definition.display_order
        rules[definition.code] = row
    session.flush()
    return rules


def _required(payload: dict[str, Any], key: str, *, position: int | None = None) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        location = f"rule at position {position}" if position else "quality catalogue"
        raise QualityCatalogueError(f"{location} is missing a valid {key}")
    return value.strip()
