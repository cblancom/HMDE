"""Validation of the selected normalization run and quality inputs."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from hmde.models import NormalizationRun

from .catalogue import RuleCatalogue, load_rule_catalogue
from .errors import QualityInputError

DATA_DIR = Path(__file__).resolve().parents[4] / "data"


@dataclass(frozen=True, slots=True)
class QualityInputs:
    normalization_run: NormalizationRun
    catalogue: RuleCatalogue
    exceptions_path: Path
    active_seed_bands: int


def load_quality_inputs(
    session: Session,
    *,
    normalization_run_id: uuid.UUID,
    rules_path: Path,
    exceptions_path: Path,
    seed_list_path: Path | None = None,
) -> QualityInputs:
    run = session.get(NormalizationRun, normalization_run_id)
    if run is None:
        raise QualityInputError(f"normalization run does not exist: {normalization_run_id}")
    if run.status not in {"completed", "completed_with_review"}:
        raise QualityInputError(f"normalization run {run.id} is not terminal: {run.status!r}")
    if not run.dataset_version or not run.taxonomy_version or not run.seed_list_version:
        raise QualityInputError(f"normalization run {run.id} is missing version metadata")
    path = seed_list_path or DATA_DIR / "seed-lists" / f"v{run.seed_list_version}.json"
    active_seed_bands = _active_seed_bands(path, expected_version=run.seed_list_version)
    catalogue = load_rule_catalogue(rules_path)
    return QualityInputs(
        normalization_run=run,
        catalogue=catalogue,
        exceptions_path=exceptions_path,
        active_seed_bands=active_seed_bands,
    )


def _active_seed_bands(path: Path, *, expected_version: str) -> int:
    if not path.is_file():
        raise QualityInputError(f"seed list does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualityInputError(f"could not read seed list: {path}") from exc
    if not isinstance(payload, dict):
        raise QualityInputError("seed-list root must be an object")
    version = payload.get("version")
    if version != expected_version:
        raise QualityInputError(
            f"seed-list version mismatch: run {expected_version!r}, seed list {version!r}"
        )
    bands = payload.get("bands")
    if not isinstance(bands, list) or not bands:
        raise QualityInputError("seed list must contain a non-empty bands array")
    if not all(isinstance(band, dict) for band in bands):
        raise QualityInputError("seed-list bands must be objects")
    total_bands = payload.get("total_bands")
    if total_bands is not None and total_bands != len(bands):
        raise QualityInputError("seed-list total_bands does not match bands")
    return sum(1 for band in bands if band.get("lifecycle") == "active")
