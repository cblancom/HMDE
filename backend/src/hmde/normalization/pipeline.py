"""Normalization run lifecycle and dry-run orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from hmde.models import NormalizationRun, TaxonomyVersion

from .aggregates import derive_band_aggregates
from .classification import classify_albums
from .credits import normalize_credits
from .entities import normalize_entities
from .errors import NormalizationError
from .inputs import NormalizationInputs
from .membership import sync_membership
from .report import write_normalization_report
from .seed import SeedMembership


@dataclass(frozen=True, slots=True)
class NormalizationRunResult:
    run_id: uuid.UUID
    status: str
    counters: dict[str, int]
    dry_run: bool
    report_path: str | None = None


class NormalizationRunner:
    def __init__(
        self,
        session: Session,
        inputs: NormalizationInputs,
        *,
        code_version: str,
    ) -> None:
        self._session = session
        self._inputs = inputs
        self._code_version = code_version

    def dry_run(self) -> NormalizationRunResult:
        run = start_normalization_run(
            self._session,
            self._inputs,
            code_version=self._code_version,
            mode="dry-run",
        )
        counters = _input_counters(self._inputs)
        finish_normalization_run(
            self._session,
            run,
            status="completed",
            counters=counters,
        )
        return NormalizationRunResult(
            run_id=run.id,
            status=run.status,
            counters=counters,
            dry_run=True,
        )

    def run(
        self,
        *,
        seed_list: SeedMembership | None = None,
        output_dir: Path | None = None,
    ) -> NormalizationRunResult:
        run = start_normalization_run(
            self._session,
            self._inputs,
            code_version=self._code_version,
            mode="full",
        )
        index = normalize_entities(self._session, self._inputs)
        credits = normalize_credits(self._session, self._inputs, index)
        classification = classify_albums(
            self._session,
            self._inputs,
            index,
            run_id=run.id,
        )
        seed_subgenres = (
            {band.mbid: band.seed_subgenre_code for band in seed_list.bands}
            if seed_list is not None
            else {}
        )
        aggregates = derive_band_aggregates(
            self._session,
            self._inputs,
            index,
            run_id=run.id,
            seed_subgenres=seed_subgenres,
        )
        membership = (
            sync_membership(
                self._session,
                dataset_version=self._inputs.dataset.dataset_version,
                seed_list=seed_list,
                artist_ids=index.artists,
            )
            if seed_list is not None
            else None
        )
        issues = list(classification.issues) + list(aggregates.issues)
        review_required = (
            classification.counts.review > 0
            or classification.counts.quarantined > 0
            or aggregates.counts.review > 0
            or aggregates.counts.missing > 0
        )
        status = "completed_with_review" if review_required else "completed"
        counters = _input_counters(self._inputs)
        counters.update(
            {
                "artists_created": index.counts.artists_created,
                "artists_updated": index.counts.artists_updated,
                "credits_created": credits.counts.created,
                "credits_quarantined": credits.counts.quarantined,
                "classified_accepted": classification.counts.accepted,
                "classified_review": classification.counts.review,
                "classified_quarantined": classification.counts.quarantined,
                "aggregates_accepted": aggregates.counts.accepted,
                "aggregates_review": aggregates.counts.review,
                "issues": len(issues),
            }
        )
        finish_normalization_run(
            self._session,
            run,
            status=status,
            counters=counters,
        )
        report_path = None
        if output_dir is not None:
            report = write_normalization_report(
                output_dir,
                run=run,
                dataset_version=self._inputs.dataset.dataset_version,
                taxonomy_version=self._inputs.dataset.taxonomy_version,
                tag_map_version=self._inputs.tag_map.version,
                overrides_version=self._inputs.overrides.version,
                index=index,
                credits=credits,
                classification=classification,
                aggregates=aggregates,
                membership=membership,
                issues=issues,
            )
            report_path = str(report.json_path)
            run.report_path = report_path
            self._session.flush()
        return NormalizationRunResult(
            run_id=run.id,
            status=run.status,
            counters=counters,
            dry_run=False,
            report_path=report_path,
        )


def start_normalization_run(
    session: Session,
    inputs: NormalizationInputs,
    *,
    code_version: str,
    mode: str,
) -> NormalizationRun:
    taxonomy = session.get(TaxonomyVersion, inputs.dataset.taxonomy_version)
    if taxonomy is None:
        raise NormalizationError(
            f"taxonomy version is not persisted: {inputs.dataset.taxonomy_version!r}"
        )
    run = NormalizationRun(
        id=uuid.uuid4(),
        dataset_version=inputs.dataset.dataset_version,
        manifest_sha256=inputs.dataset.manifest_sha256,
        seed_list_version=inputs.dataset.seed_list_version,
        taxonomy_version=inputs.dataset.taxonomy_version,
        tag_map_version=inputs.tag_map.version,
        overrides_version=inputs.overrides.version,
        status="running",
        code_version=code_version,
        parameters={
            "mode": mode,
            "dataset_path": str(inputs.dataset.root),
            "taxonomy_path": str(inputs.taxonomy_path),
            "tag_map_path": str(inputs.tag_map.path),
            "overrides_path": str(inputs.overrides.path),
            "batch_ids": list(inputs.dataset.batch_ids),
        },
        counters=_input_counters(inputs),
    )
    session.add(run)
    session.flush()
    return run


def finish_normalization_run(
    session: Session,
    run: NormalizationRun,
    *,
    status: str,
    counters: dict[str, int],
    report_path: str | None = None,
) -> None:
    if status not in {"completed", "completed_with_review", "failed"}:
        raise NormalizationError(f"invalid terminal run status: {status!r}")
    run.status = status
    run.finished_at = datetime.now(UTC)
    run.counters = counters
    run.report_path = report_path
    session.flush()


def _input_counters(inputs: NormalizationInputs) -> dict[str, int]:
    return {
        "bands": inputs.dataset.band_count,
        "artists": inputs.dataset.file("artists.ndjson").count,
        "release_groups": inputs.dataset.file("release_groups.ndjson").count,
        "releases": inputs.dataset.file("releases.ndjson").count,
        "recordings": inputs.dataset.file("recordings.ndjson").count,
        "release_recordings": inputs.dataset.file("release_recordings.ndjson").count,
        "credits": inputs.dataset.file("credits.ndjson").count,
        "external_ids": inputs.dataset.file("external_ids.ndjson").count,
    }
