"""Seed a disposable database for deterministic Playwright end-to-end tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import Artist, NormalizationRun, QualityRuleCatalogue, QualityRun
from hmde.network.inputs import NetworkInputs
from hmde.network.runner import run_network
from hmde.normalization.taxonomy import sync_taxonomy
from hmde.seed.loader import load_fixtures

ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = ROOT / "data" / "fixtures" / "e2"
TAXONOMY_PATH = ROOT / "data" / "taxonomy.json"
NORMALIZATION_RUN_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
QUALITY_RUN_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
DATASET_VERSION = "e2e-fixture"


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise SystemExit("DATABASE_URL is required")
    url = make_url(value)
    if "e2e" not in (url.database or ""):
        raise SystemExit(f"refusing to seed a non-e2e database: {url.database!r}")
    return value


def _manifest_hash() -> str:
    return hashlib.sha256((FIXTURES_DIR / "manifest.json").read_bytes()).hexdigest()


def _load_catalog(session: Session) -> None:
    artist_count = session.scalar(select(func.count()).select_from(Artist)) or 0
    if artist_count == 0:
        load_fixtures(FIXTURES_DIR, session)


def _seed_runs(session: Session) -> None:
    sync_taxonomy(session, TAXONOMY_PATH, make_current=True)

    normalization = NormalizationRun(
        id=NORMALIZATION_RUN_ID,
        dataset_version=DATASET_VERSION,
        manifest_sha256=_manifest_hash(),
        seed_list_version="e2.0.0",
        taxonomy_version="0.2.0",
        tag_map_version="0.1.0",
        overrides_version="0.1.0",
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        code_version="e2e-seed",
    )
    session.merge(normalization)
    session.merge(
        QualityRuleCatalogue(
            version="0.1.0",
            schema_version=1,
            source_hash="0" * 64,
            source_path="data/quality/rules-v0.1.0.json",
        )
    )
    session.flush()

    quality = QualityRun(
        id=QUALITY_RUN_ID,
        normalization_run_id=NORMALIZATION_RUN_ID,
        dataset_version=DATASET_VERSION,
        taxonomy_version="0.2.0",
        catalogue_version="0.1.0",
        code_version="e2e-seed",
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        parameters={},
        counters={},
    )
    session.merge(quality)
    session.flush()

    inputs = NetworkInputs(
        normalization_run=normalization,
        quality_run=quality,
        taxonomy_path=TAXONOMY_PATH,
        taxonomy_version="0.2.0",
    )
    result = run_network(
        session,
        inputs,
        code_version="e2e-seed",
        output_dir=Path("/tmp/hmde-e2e-network"),
    )
    print(
        json.dumps(
            {
                "analysis_run_id": str(result.run_id),
                "analysis_version": result.analysis_version,
                "status": result.status,
                "reused": result.reused,
                "taxonomy_version": "0.2.0",
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=None, help="defaults to DATABASE_URL")
    args = parser.parse_args()
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    engine = create_engine(_database_url(), pool_pre_ping=True)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        with factory() as session:
            _load_catalog(session)
            _seed_runs(session)
            session.commit()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
