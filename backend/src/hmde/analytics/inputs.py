"""Validation of normalization, quality and metric-catalogue inputs."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from hmde.models import NormalizationRun, QualityRun

from .catalogue import MetricCatalogue, load_metric_catalogue
from .errors import AnalysisInputError


@dataclass(frozen=True, slots=True)
class AnalysisInputs:
    normalization_run: NormalizationRun
    quality_run: QualityRun
    catalogue: MetricCatalogue
    taxonomy_path: Path


def load_analysis_inputs(
    session: Session,
    *,
    normalization_run_id: uuid.UUID,
    quality_run_id: uuid.UUID,
    taxonomy_path: Path,
    metric_catalogue_path: Path,
) -> AnalysisInputs:
    normalization = session.get(NormalizationRun, normalization_run_id)
    if normalization is None:
        raise AnalysisInputError(f"normalization run does not exist: {normalization_run_id}")
    if normalization.status not in {"completed", "completed_with_review"}:
        raise AnalysisInputError(
            f"normalization run {normalization.id} is not terminal: {normalization.status!r}"
        )
    quality = session.get(QualityRun, quality_run_id)
    if quality is None:
        raise AnalysisInputError(f"quality run does not exist: {quality_run_id}")
    if quality.status not in {"completed", "completed_with_findings"}:
        raise AnalysisInputError(f"quality run {quality.id} is not acceptable: {quality.status!r}")
    if quality.normalization_run_id != normalization.id:
        raise AnalysisInputError("quality run belongs to a different normalization run")
    if quality.dataset_version != normalization.dataset_version:
        raise AnalysisInputError("quality and normalization dataset versions differ")
    if quality.taxonomy_version != normalization.taxonomy_version:
        raise AnalysisInputError("quality and normalization taxonomy versions differ")
    taxonomy_version = _taxonomy_version(taxonomy_path)
    if taxonomy_version != normalization.taxonomy_version:
        raise AnalysisInputError(
            f"taxonomy version mismatch: run {normalization.taxonomy_version!r}, "
            f"file {taxonomy_version!r}"
        )
    catalogue = load_metric_catalogue(metric_catalogue_path)
    return AnalysisInputs(
        normalization_run=normalization,
        quality_run=quality,
        catalogue=catalogue,
        taxonomy_path=taxonomy_path,
    )


def _taxonomy_version(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisInputError(f"could not read taxonomy: {path}") from exc
    version = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise AnalysisInputError("taxonomy is missing a valid version")
    return version.strip()
