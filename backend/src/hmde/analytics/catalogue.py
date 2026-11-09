"""Versioned E6 metric catalogue."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .errors import MetricCatalogueError

REQUIRED_FIELDS = (
    "code",
    "name",
    "description",
    "numerator",
    "denominator",
    "unit",
    "scope",
    "filters",
    "interpretation",
    "limitations",
)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    code: str
    name: str
    description: str
    numerator: str
    denominator: str
    unit: str
    scope: str
    filters: str
    interpretation: str
    limitations: str


@dataclass(frozen=True, slots=True)
class MetricCatalogue:
    version: str
    source_hash: str
    source_path: str
    metrics: tuple[MetricDefinition, ...]

    def by_code(self) -> dict[str, MetricDefinition]:
        return {metric.code: metric for metric in self.metrics}


def load_metric_catalogue(path: Path) -> MetricCatalogue:
    if not path.is_file():
        raise MetricCatalogueError(f"metric catalogue does not exist: {path}")
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MetricCatalogueError(f"could not read metric catalogue: {path}") from exc
    if not isinstance(payload, dict):
        raise MetricCatalogueError("metric catalogue root must be an object")
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        raise MetricCatalogueError("metric catalogue is missing a valid version")
    raw_metrics = payload.get("metrics")
    if not isinstance(raw_metrics, list) or not raw_metrics:
        raise MetricCatalogueError("metric catalogue must contain metrics")
    metrics: list[MetricDefinition] = []
    seen: set[str] = set()
    for index, raw_metric in enumerate(raw_metrics, start=1):
        if not isinstance(raw_metric, dict):
            raise MetricCatalogueError(f"metric at position {index} must be an object")
        missing = [field for field in REQUIRED_FIELDS if not _text(raw_metric.get(field))]
        if missing:
            raise MetricCatalogueError(
                f"metric at position {index} is missing fields: {', '.join(missing)}"
            )
        code = _text(raw_metric["code"])
        if code in seen:
            raise MetricCatalogueError(f"duplicate metric code: {code}")
        seen.add(code)
        metrics.append(
            MetricDefinition(
                code=code,
                name=_text(raw_metric["name"]),
                description=_text(raw_metric["description"]),
                numerator=_text(raw_metric["numerator"]),
                denominator=_text(raw_metric["denominator"]),
                unit=_text(raw_metric["unit"]),
                scope=_text(raw_metric["scope"]),
                filters=_text(raw_metric["filters"]),
                interpretation=_text(raw_metric["interpretation"]),
                limitations=_text(raw_metric["limitations"]),
            )
        )
    return MetricCatalogue(
        version=version.strip(),
        source_hash=hashlib.sha256(raw).hexdigest(),
        source_path=str(path),
        metrics=tuple(metrics),
    )


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    return value.strip()
