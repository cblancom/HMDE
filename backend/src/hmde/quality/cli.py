"""Quality CLI and end-to-end execution."""

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

from .inputs import load_quality_inputs
from .runner import QualityRunResult, run_quality

DEFAULT_RULES = Path("../data/quality/rules-v0.1.0.json")
DEFAULT_EXCEPTIONS = Path("../data/quality/exceptions-v0.1.0.json")
DEFAULT_OUTPUT = Path("../data/quality")

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class QualityOptions:
    normalization_run: uuid.UUID
    rules: Path
    exceptions: Path
    output: Path
    strict: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hmde.quality",
        description="Run data-quality validation over the normalized corpus.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run a quality assessment")
    run.add_argument("--normalization-run", type=uuid.UUID, required=True)
    run.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    run.add_argument("--exceptions", type=Path, default=DEFAULT_EXCEPTIONS)
    run.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    run.add_argument("--strict", action="store_true")
    return parser


def execute_quality(
    session: Session,
    options: QualityOptions,
    *,
    code_version: str,
) -> QualityRunResult:
    inputs = load_quality_inputs(
        session,
        normalization_run_id=options.normalization_run,
        rules_path=options.rules,
        exceptions_path=options.exceptions,
    )
    return run_quality(
        session,
        inputs,
        code_version=code_version,
        strict=options.strict,
        output_dir=options.output,
    )


def run_cli(
    options: QualityOptions,
    settings: Settings,
    *,
    session_factory: sessionmaker[Session] | None = None,
    code_version: str | None = None,
) -> int:
    factory = session_factory or _session_factory(settings.database_url)
    code = code_version or current_code_version()
    with factory() as session:
        try:
            result = execute_quality(session, options, code_version=code)
            session.commit()
        except Exception:
            session.rollback()
            raise
    if result.report_path:
        logger.info("Wrote quality report %s", result.report_path)
    if result.status == "completed":
        return 0
    if result.status == "completed_with_findings":
        return 2
    if result.status == "blocked":
        return 3
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
    options = QualityOptions(
        normalization_run=args.normalization_run,
        rules=args.rules,
        exceptions=args.exceptions,
        output=args.output,
        strict=args.strict,
    )
    settings = get_settings()
    try:
        return run_cli(options, settings)
    except Exception:
        logger.exception("Quality assessment failed")
        return 1
