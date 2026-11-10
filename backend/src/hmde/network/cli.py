"""Network analysis CLI."""

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

from .inputs import load_network_inputs
from .runner import NetworkRunResult, run_network

DEFAULT_TAXONOMY = Path("../data/taxonomy.json")
DEFAULT_OUTPUT = Path("../data/network")

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NetworkOptions:
    normalization_run: uuid.UUID
    quality_run: uuid.UUID
    taxonomy: Path
    output: Path
    top_k: int
    decade: str | None
    subgenre: str | None
    bands: tuple[uuid.UUID, ...]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hmde.network",
        description="Build producer-centric network layers over the normalized corpus.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run E7 network analysis")
    run.add_argument("--normalization-run", type=uuid.UUID, required=True)
    run.add_argument("--quality-run", type=uuid.UUID, required=True)
    run.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    run.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    run.add_argument("--top-k", type=int, default=20)
    run.add_argument("--decade", type=str, default=None)
    run.add_argument("--subgenre", type=str, default=None)
    run.add_argument("--band", dest="bands", type=uuid.UUID, action="append", default=[])
    return parser


def execute_network(
    session: Session,
    options: NetworkOptions,
    *,
    code_version: str,
) -> NetworkRunResult:
    inputs = load_network_inputs(
        session,
        normalization_run_id=options.normalization_run,
        quality_run_id=options.quality_run,
        taxonomy_path=options.taxonomy,
    )
    return run_network(
        session,
        inputs,
        code_version=code_version,
        output_dir=options.output,
        top_k=options.top_k,
        decade=options.decade,
        subgenre=options.subgenre,
        band_ids=options.bands,
    )


def run_cli(
    options: NetworkOptions,
    settings: Settings,
    *,
    session_factory: sessionmaker[Session] | None = None,
    code_version: str | None = None,
) -> int:
    factory = session_factory or _session_factory(settings.database_url)
    code = code_version or current_code_version()
    with factory() as session:
        try:
            result = execute_network(session, options, code_version=code)
            session.commit()
        except Exception:
            session.rollback()
            raise
    if result.report_path:
        logger.info("Wrote network report %s", result.report_path)
    if result.status == "completed":
        return 0
    if result.status == "completed_with_limitations":
        return 2
    return 1


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
    options = NetworkOptions(
        normalization_run=args.normalization_run,
        quality_run=args.quality_run,
        taxonomy=args.taxonomy,
        output=args.output,
        top_k=args.top_k,
        decade=args.decade,
        subgenre=args.subgenre,
        bands=tuple(args.bands),
    )
    settings = get_settings()
    try:
        return run_cli(options, settings)
    except Exception:
        logger.exception("Network analysis failed")
        return 1
