"""End-to-end MusicBrainz ingestion pipeline."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.core.config import Settings
from hmde.etl.musicbrainz.cli import IngestOptions, IngestRunner, IngestRunResult
from hmde.etl.musicbrainz.client import MusicBrainzClient
from hmde.etl.musicbrainz.dataset import DatasetWriteResult, write_dataset
from hmde.etl.musicbrainz.rate_limit import RateLimiter
from hmde.etl.musicbrainz.raw_store import RawStore
from hmde.etl.musicbrainz.report import ReportResult, write_report
from hmde.etl.musicbrainz.seed import SeedBand, SeedList
from hmde.etl.musicbrainz.traversal import (
    PERIOD_END_YEAR,
    PERIOD_START_YEAR,
    BandExtraction,
    MusicBrainzTraversal,
)
from hmde.models import IngestError, IngestRun, RawResponse

HttpClientFactory = Callable[[], Any]


@dataclass(frozen=True, slots=True)
class PipelineResult:
    run: IngestRunResult
    dataset: DatasetWriteResult | None
    report: ReportResult | None


class IngestPipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: sessionmaker[Session],
        seed_list: SeedList,
        options: IngestOptions,
        code_version: str,
        http_client_factory: HttpClientFactory | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._seed_list = seed_list
        self._options = options
        self._code_version = code_version
        self._http_client_factory = http_client_factory
        self._rate_limiter = RateLimiter(settings.musicbrainz_min_interval_seconds)

    def run(self) -> PipelineResult:
        extractions: dict[str, BandExtraction] = {}

        period_start_year = (
            self._seed_list.period_start.year
            if self._seed_list.period_start is not None
            else PERIOD_START_YEAR
        )
        period_end_year = (
            self._seed_list.period_end.year
            if self._seed_list.period_end is not None
            else PERIOD_END_YEAR
        )

        def processor(session: Session, band: SeedBand, run_id: uuid.UUID) -> None:
            http_client = self._http_client_factory() if self._http_client_factory else None
            raw_store = RawStore(session, self._options.raw_root)
            client = MusicBrainzClient(
                settings=self._settings,
                raw_store=raw_store,
                ingest_run_id=run_id,
                cache_only=self._options.cache_only,
                refresh=self._options.refresh,
                http_client=http_client,
                rate_limiter=self._rate_limiter,
            )
            try:
                extraction = MusicBrainzTraversal(
                    client,
                    period_start_year=period_start_year,
                    period_end_year=period_end_year,
                ).extract_band(band)
            except Exception:
                session.commit()
                raise
            finally:
                client.close()
                if http_client is not None:
                    http_client.close()
            extractions[band.mbid] = extraction

        runner = IngestRunner(
            session_factory=self._session_factory,
            seed_list=self._seed_list,
            options=self._options,
            code_version=self._code_version,
        )
        run_result = runner.run(processor)

        if not extractions:
            return PipelineResult(run=run_result, dataset=None, report=None)

        raw_ids = _extraction_raw_ids(extractions.values())
        source_snapshot_at = self._source_snapshot_at(run_result.run_id, raw_ids)
        dataset = write_dataset(
            extractions.values(),
            self._options.output,
            seed_list_version=self._seed_list.version,
            taxonomy_version=self._seed_list.taxonomy_version,
            period_start=(
                self._seed_list.period_start.isoformat()
                if self._seed_list.period_start is not None
                else None
            ),
            period_end=(
                self._seed_list.period_end.isoformat()
                if self._seed_list.period_end is not None
                else None
            ),
            batch_ids=tuple(batch.batch_id for batch in self._seed_list.batches),
            source_snapshot_at=source_snapshot_at,
            code_version=self._code_version,
        )
        failures = self._failures(run_result.run_id)
        counters = self._update_run(
            run_result.run_id,
            dataset=dataset,
            source_snapshot_at=source_snapshot_at,
            raw_ids=raw_ids,
            extractions=extractions.values(),
        )
        report = write_report(
            dataset.path,
            extractions.values(),
            dataset_version=dataset.dataset_version,
            seed_list_version=self._seed_list.version,
            taxonomy_version=self._seed_list.taxonomy_version,
            period_start=(
                self._seed_list.period_start.isoformat()
                if self._seed_list.period_start is not None
                else None
            ),
            period_end=(
                self._seed_list.period_end.isoformat()
                if self._seed_list.period_end is not None
                else None
            ),
            batch_ids=tuple(batch.batch_id for batch in self._seed_list.batches),
            source_snapshot_at=source_snapshot_at,
            code_version=self._code_version,
            counters=counters,
            failures=failures,
        )
        return PipelineResult(run=run_result, dataset=dataset, report=report)

    def _source_snapshot_at(self, run_id: uuid.UUID, raw_ids: set[uuid.UUID]) -> datetime:
        with self._session_factory() as session:
            value = session.scalar(
                select(func.max(RawResponse.fetched_at)).where(RawResponse.id.in_(raw_ids))
            )
        return value or datetime.now(UTC)

    def _failures(self, run_id: uuid.UUID) -> list[dict[str, object]]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(IngestError).where(IngestError.ingest_run_id == run_id)
            ).all()
        return [
            {
                "band_mbid": row.band_mbid,
                "phase": row.phase,
                "error_type": row.error_type,
                "message": row.message,
                "attempts": row.attempts,
            }
            for row in rows
        ]

    def _update_run(
        self,
        run_id: uuid.UUID,
        *,
        dataset: DatasetWriteResult,
        source_snapshot_at: datetime,
        raw_ids: set[uuid.UUID],
        extractions,
    ) -> dict[str, object]:
        extraction_list = list(extractions)
        with self._session_factory() as session:
            run = session.get(IngestRun, run_id)
            if run is None:
                raise RuntimeError(f"ingest run disappeared: {run_id}")
            raw_rows = session.scalars(select(RawResponse).where(RawResponse.id.in_(raw_ids))).all()
            new_raw = sum(1 for row in raw_rows if row.first_ingest_run_id == run_id)
            counters = dict(run.counters or {})
            counters.update(
                {
                    "bands_extracted": len(extraction_list),
                    "release_groups": sum(len(item.release_groups) for item in extraction_list),
                    "releases": sum(len(item.releases) for item in extraction_list),
                    "recordings": sum(len(item.recordings) for item in extraction_list),
                    "credits": sum(len(item.credits) for item in extraction_list),
                    "places": sum(len(item.places) for item in extraction_list),
                    "exclusions": sum(len(item.exclusions) for item in extraction_list),
                    "raw_responses": len(raw_rows),
                    "raw_responses_new": new_raw,
                    "raw_responses_reused": len(raw_rows) - new_raw,
                }
            )
            run.dataset_version = dataset.dataset_version
            run.source_snapshot_at = source_snapshot_at
            run.output_path = str(dataset.path)
            run.counters = counters
            session.commit()
            return counters


def _extraction_raw_ids(extractions) -> set[uuid.UUID]:
    ids: set[uuid.UUID] = set()
    for extraction in extractions:
        ids.add(extraction.artist.raw_response_id)
        for values in (
            extraction.external_ids,
            extraction.release_groups,
            extraction.releases,
            extraction.recordings,
            extraction.release_recordings,
            extraction.credits,
            extraction.places,
            extraction.exclusions,
        ):
            ids.update(item.raw_response_id for item in values)
    return ids
