"""EDA CLI."""

from __future__ import annotations

import argparse
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hmde.core.config import Settings, get_settings

from .inputs import load_analysis_inputs
from .runner import AnalysisResult, run_analysis

DEFAULT_TAXONOMY = Path("../data/taxonomy.json")
DEFAULT_CATALOGUE = Path("../data/metrics/catalogue-v0.1.0.json")
DEFAULT_OUTPUT = Path("../data/analysis")

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnalysisOptions:
    normalization_run: uuid.UUID
    quality_run: uuid.UUID
    taxonomy: Path
    catalogue: Path
    output: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hmde.analytics",
        description="Run exploratory analysis over the normalized corpus.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run EDA")
    run.add_argument("--normalization-run", type=uuid.UUID, required=True)
    run.add_argument("--quality-run", type=uuid.UUID, required=True)
    run.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    run.add_argument("--metric-catalogue", dest="catalogue", type=Path, default=DEFAULT_CATALOGUE)
    run.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def execute_analysis(
    session: Session,
    options: AnalysisOptions,
    *,
    code_version: str,
) -> AnalysisResult:
    inputs = load_analysis_inputs(
        session,
        normalization_run_id=options.normalization_run,
        quality_run_id=options.quality_run,
        taxonomy_path=options.taxonomy,
        metric_catalogue_path=options.catalogue,
    )
    return run_analysis(
        session,
        inputs,
        code_version=code_version,
        output_dir=options.output,
    )


def run_cli(
    options: AnalysisOptions,
    settings: Settings,
    *,
    session_factory: sessionmaker[Session] | None = None,
    code_version: str | None = None,
) -> int:
    factory = session_factory or _session_factory(settings.database_url)
    code = code_version or current_code_version()
    with factory() as session:
        result = execute_analysis(session, options, code_version=code)
        session.rollback()
    logger.info("Wrote EDA report %s", result.report_path)
    return 2 if result.advisory else 0


def current_code_version() -> str:
    try:
        return version("hmde-backend")
    except PackageNotFoundError:
        return "unknown"


def _session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = AnalysisOptions(
        normalization_run=args.normalization_run,
        quality_run=args.quality_run,
        taxonomy=args.taxonomy,
        catalogue=args.catalogue,
        output=args.output,
    )
    settings = get_settings()
    try:
        return run_cli(options, settings)
    except Exception:
        logger.exception("EDA failed")
        return 1
