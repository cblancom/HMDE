"""Validation of the selected normalization run and quality inputs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from hmde.models import NormalizationRun

from .catalogue import RuleCatalogue, load_rule_catalogue
from .errors import QualityInputError


@dataclass(frozen=True, slots=True)
class QualityInputs:
    normalization_run: NormalizationRun
    catalogue: RuleCatalogue
    exceptions_path: Path


def load_quality_inputs(
    session: Session,
    *,
    normalization_run_id: uuid.UUID,
    rules_path: Path,
    exceptions_path: Path,
) -> QualityInputs:
    run = session.get(NormalizationRun, normalization_run_id)
    if run is None:
        raise QualityInputError(f"normalization run does not exist: {normalization_run_id}")
    if run.status not in {"completed", "completed_with_review"}:
        raise QualityInputError(f"normalization run {run.id} is not terminal: {run.status!r}")
    if not run.dataset_version or not run.taxonomy_version:
        raise QualityInputError(f"normalization run {run.id} is missing version metadata")
    catalogue = load_rule_catalogue(rules_path)
    return QualityInputs(
        normalization_run=run,
        catalogue=catalogue,
        exceptions_path=exceptions_path,
    )
