"""Normalization CLI and end-to-end execution."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hmde.core.config import Settings, get_settings

from .errors import NormalizationError
from .inputs import validate_inputs
from .pipeline import NormalizationRunner, NormalizationRunResult
from .seed import load_seed_membership
from .taxonomy import sync_taxonomy

DEFAULT_DATASET = Path("../data/ingestions/musicbrainz/mb-20261107T194927Z-0d6cedd5c261")
DEFAULT_TAXONOMY = Path("../data/taxonomy.json")
DEFAULT_TAG_MAP = Path("../data/classifications/tag-map-v0.1.0.json")
DEFAULT_OVERRIDES = Path("../data/classifications/manual-overrides-v0.1.0.json")
DEFAULT_SEED_LIST = Path("../data/seed-list.json")
DEFAULT_OUTPUT = Path("../data/normalization")

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NormalizationOptions:
    dataset: Path
    taxonomy: Path
    tag_map: Path
    overrides: Path
    seed_list: Path
    output: Path
    dry_run: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m hmde.normalization",
        description="Normalize the E3 dataset into canonical entities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run normalization")
    run.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    run.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    run.add_argument("--tag-map", type=Path, default=DEFAULT_TAG_MAP)
    run.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    run.add_argument("--seed-list", type=Path, default=DEFAULT_SEED_LIST)
    run.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    run.add_argument("--dry-run", action="store_true")
    return parser


def execute_normalization(
    session: Session,
    options: NormalizationOptions,
    *,
    code_version: str,
) -> NormalizationRunResult:
    inputs = validate_inputs(
        options.dataset,
        taxonomy_path=options.taxonomy,
        tag_map_path=options.tag_map,
        overrides_path=options.overrides,
    )
    seed_list = load_seed_membership(options.seed_list)
    if seed_list.version != inputs.dataset.seed_list_version:
        raise NormalizationError(
            f"seed-list version mismatch: dataset {inputs.dataset.seed_list_version!r}, "
            f"seed list {seed_list.version!r}"
        )
    sync_taxonomy(session, inputs.taxonomy_path)
    runner = NormalizationRunner(session, inputs, code_version=code_version)
    if options.dry_run:
        return runner.dry_run()
    return runner.run(seed_list=seed_list, output_dir=options.output)


def run_cli(
    options: NormalizationOptions,
    settings: Settings,
    *,
    session_factory: sessionmaker[Session] | None = None,
    code_version: str | None = None,
) -> int:
    factory = session_factory or _session_factory(settings.database_url)
    version_string = code_version or current_code_version()
    with factory() as session:
        try:
            result = execute_normalization(session, options, code_version=version_string)
            session.commit()
        except Exception:
            session.rollback()
            raise
    if result.report_path is not None:
        logger.info("Wrote normalization report %s", result.report_path)
    if result.status == "completed":
        return 0
    if result.status == "completed_with_review":
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
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()
    options = NormalizationOptions(
        dataset=args.dataset,
        taxonomy=args.taxonomy,
        tag_map=args.tag_map,
        overrides=args.overrides,
        seed_list=args.seed_list,
        output=args.output,
        dry_run=args.dry_run,
    )
    try:
        return run_cli(options, settings)
    except Exception:
        logger.exception("Normalization failed")
        return 1
