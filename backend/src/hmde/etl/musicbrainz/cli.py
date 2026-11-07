"""MusicBrainz ingestion CLI."""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from hmde.core.config import Settings, get_settings
from hmde.core.logging import configure_logging
from hmde.etl.musicbrainz.seed import SeedBand, SeedList, load_seed_list, select_bands
from hmde.models import IngestError, IngestRun

DEFAULT_SEED_LIST = Path("../data/seed-list.json")
DEFAULT_OUTPUT = Path("../data/ingestions/musicbrainz")
DEFAULT_RAW_ROOT = Path("../data/raw/musicbrainz")

logger = logging.getLogger(__name__)

BandProcessor = Callable[[Session, SeedBand, uuid.UUID], None]


@dataclass(frozen=True, slots=True)
class IngestRunResult:
    run_id: uuid.UUID
    status: str
    processed_bands: int
    failed_bands: int


@dataclass(frozen=True, slots=True)
class IngestOptions:
    seed_list: Path
    output: Path
    bands: tuple[str, ...]
    max_bands: int | None
    cache_only: bool
    refresh: bool
    raw_root: Path = DEFAULT_RAW_ROOT


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hmde.etl.musicbrainz",
        description="Ingest the HMDE seed list from MusicBrainz.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest", help="run a MusicBrainz ingestion")
    ingest.add_argument(
        "--seed-list",
        type=Path,
        default=DEFAULT_SEED_LIST,
        help="path to the versioned seed list",
    )
    ingest.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="directory for raw references and extracted datasets",
    )
    ingest.add_argument(
        "--band",
        dest="bands",
        action="append",
        default=[],
        help="limit ingestion to a band MBID; repeatable",
    )
    ingest.add_argument(
        "--max-bands",
        type=_positive_int,
        default=None,
        help="limit the number of seed bands processed",
    )
    ingest.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help="directory for immutable raw MusicBrainz responses",
    )
    mode = ingest.add_mutually_exclusive_group()
    mode.add_argument(
        "--cache-only",
        action="store_true",
        help="use stored raw responses and make no network requests",
    )
    mode.add_argument(
        "--refresh",
        action="store_true",
        help="fetch fresh responses instead of reusing cached raw data",
    )
    return parser


def validate_runtime_settings(settings: Settings, *, cache_only: bool) -> str | None:
    if cache_only:
        return None
    if not settings.musicbrainz_user_agent:
        return (
            "MUSICBRAINZ_USER_AGENT is required for live ingestion. "
            "Use a project name/version and contact details."
        )
    return None


class IngestRunner:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        seed_list: SeedList,
        options: IngestOptions,
        code_version: str,
    ) -> None:
        self._session_factory = session_factory
        self._seed_list = seed_list
        self._options = options
        self._code_version = code_version

    def run(self, processor: BandProcessor) -> IngestRunResult:
        selected = select_bands(
            self._seed_list,
            self._options.bands,
            self._options.max_bands,
        )
        run_id = uuid.uuid4()
        initial_counters = {
            "bands_total": len(selected),
            "bands_processed": 0,
            "bands_failed": 0,
        }
        parameters = {
            "seed_list_path": str(self._options.seed_list),
            "seed_list_version": self._seed_list.version,
            "taxonomy_version": self._seed_list.taxonomy_version,
            "period_start": (
                self._seed_list.period_start.isoformat()
                if self._seed_list.period_start is not None
                else None
            ),
            "period_end": (
                self._seed_list.period_end.isoformat()
                if self._seed_list.period_end is not None
                else None
            ),
            "batch_ids": [batch.batch_id for batch in self._seed_list.batches],
            "bands": list(self._options.bands),
            "max_bands": self._options.max_bands,
            "cache_only": self._options.cache_only,
            "refresh": self._options.refresh,
            "output": str(self._options.output),
            "raw_root": str(self._options.raw_root),
        }

        with self._session_factory() as session:
            run = IngestRun(
                id=run_id,
                seed_list_version=self._seed_list.version,
                status="running",
                code_version=self._code_version,
                parameters=parameters,
                counters=initial_counters,
                output_path=str(self._options.output),
            )
            session.add(run)
            session.commit()

        processed = 0
        failed = 0
        for band in selected:
            with self._session_factory() as session:
                try:
                    processor(session, band, run_id)
                    session.commit()
                    processed += 1
                except Exception as exc:
                    session.rollback()
                    failed += 1
                    with self._session_factory() as error_session:
                        error_session.add(
                            IngestError(
                                id=uuid.uuid4(),
                                ingest_run_id=run_id,
                                band_mbid=band.mbid,
                                phase="band",
                                error_type=type(exc).__name__,
                                message=str(exc)[:2000],
                                attempts=1,
                            )
                        )
                        error_session.commit()

        status = "completed" if failed == 0 else "completed_with_errors"
        with self._session_factory() as session:
            run = session.get(IngestRun, run_id)
            if run is None:
                raise RuntimeError(f"ingest run disappeared: {run_id}")
            run.status = status
            run.finished_at = datetime.now(UTC)
            run.counters = {
                **initial_counters,
                "bands_processed": processed,
                "bands_failed": failed,
            }
            session.commit()

        return IngestRunResult(
            run_id=run_id,
            status=status,
            processed_bands=processed,
            failed_bands=failed,
        )


def current_code_version() -> str:
    try:
        return version("hmde-backend")
    except PackageNotFoundError:
        return "unknown"


def run_ingest(
    options: IngestOptions,
    settings: Settings,
    *,
    seed_list: SeedList | None = None,
    session_factory: sessionmaker[Session] | None = None,
    http_client_factory=None,
) -> int:
    from hmde.etl.musicbrainz.pipeline import IngestPipeline

    loaded_seed_list = seed_list or load_seed_list(options.seed_list)
    factory = session_factory or _session_factory(settings.database_url)
    result = IngestPipeline(
        settings=settings,
        session_factory=factory,
        seed_list=loaded_seed_list,
        options=options,
        code_version=current_code_version(),
        http_client_factory=http_client_factory,
    ).run()

    if result.dataset is not None:
        logger.info("Wrote dataset %s", result.dataset.path)
    if result.report is not None:
        logger.info("Wrote report %s", result.report.report_path)
    logger.info(
        "Ingestion %s: %s processed, %s failed",
        result.run.status,
        result.run.processed_bands,
        result.run.failed_bands,
    )

    if result.run.status == "completed":
        return 0
    if result.run.status == "completed_with_errors":
        return 2
    return 1


def _session_factory(database_url: str) -> sessionmaker[Session]:
    from sqlalchemy import create_engine

    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    options = IngestOptions(
        seed_list=args.seed_list,
        output=args.output,
        bands=tuple(args.bands),
        max_bands=args.max_bands,
        cache_only=args.cache_only,
        refresh=args.refresh,
        raw_root=args.raw_root,
    )

    error = validate_runtime_settings(settings, cache_only=options.cache_only)
    if error:
        print(error, file=sys.stderr)
        return 1

    configure_logging(settings.log_level)
    try:
        return run_ingest(options, settings)
    except Exception:
        logger.exception("MusicBrainz ingestion failed")
        return 1
