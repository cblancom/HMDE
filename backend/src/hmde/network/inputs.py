"""Validation of normalization, quality and taxonomy inputs for E7."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from hmde.models import NormalizationRun, QualityRun

from .errors import NetworkInputError

TERMINAL_NORMALIZATION = {"completed", "completed_with_review"}
ACCEPTABLE_QUALITY = {"completed", "completed_with_findings"}


@dataclass(frozen=True, slots=True)
class NetworkInputs:
    normalization_run: NormalizationRun
    quality_run: QualityRun
    taxonomy_path: Path
    taxonomy_version: str


def load_network_inputs(
    session: Session,
    *,
    normalization_run_id: uuid.UUID,
    quality_run_id: uuid.UUID,
    taxonomy_path: Path,
) -> NetworkInputs:
    normalization = session.get(NormalizationRun, normalization_run_id)
    if normalization is None:
        raise NetworkInputError(f"normalization run does not exist: {normalization_run_id}")
    if normalization.status not in TERMINAL_NORMALIZATION:
        raise NetworkInputError(
            f"normalization run {normalization.id} is not terminal: {normalization.status!r}"
        )
    if not normalization.dataset_version or not normalization.taxonomy_version:
        raise NetworkInputError(f"normalization run {normalization.id} is missing version metadata")

    quality = session.get(QualityRun, quality_run_id)
    if quality is None:
        raise NetworkInputError(f"quality run does not exist: {quality_run_id}")
    if quality.status not in ACCEPTABLE_QUALITY:
        raise NetworkInputError(f"quality run {quality.id} is not acceptable: {quality.status!r}")
    if quality.normalization_run_id != normalization.id:
        raise NetworkInputError("quality run belongs to a different normalization run")
    if quality.dataset_version != normalization.dataset_version:
        raise NetworkInputError("quality and normalization dataset versions differ")
    if quality.taxonomy_version != normalization.taxonomy_version:
        raise NetworkInputError("quality and normalization taxonomy versions differ")

    taxonomy_version = _taxonomy_version(taxonomy_path)
    if taxonomy_version != normalization.taxonomy_version:
        raise NetworkInputError(
            f"taxonomy version mismatch: run {normalization.taxonomy_version!r}, "
            f"file {taxonomy_version!r}"
        )
    return NetworkInputs(
        normalization_run=normalization,
        quality_run=quality,
        taxonomy_path=taxonomy_path,
        taxonomy_version=taxonomy_version,
    )


def _taxonomy_version(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NetworkInputError(f"could not read taxonomy: {path}") from exc
    version = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise NetworkInputError("taxonomy is missing a valid version")
    return version.strip()
