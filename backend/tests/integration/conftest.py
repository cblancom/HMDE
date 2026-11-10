from __future__ import annotations

import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hmde.db.session import get_db
from hmde.main import app
from hmde.models import (
    NormalizationRun,
    QualityRuleCatalogue,
    QualityRun,
    TaxonomyVersion,
)
from hmde.network import GRAPH_VERSION
from hmde.network.graph import build_producer_album_layer, build_producer_band_layer
from hmde.network.inputs import NetworkInputs
from hmde.network.loader import load_network_data
from hmde.network.metrics import compute_metrics
from hmde.network.persistence import (
    analysis_version,
    persist_network_run,
    start_analysis_run,
)
from hmde.network.report import write_network_report
from hmde.seed.loader import load_fixtures

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "e2"


def _run_alembic(*args: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = TEST_DATABASE_URL or ""
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def test_database_url() -> str:
    database_url = TEST_DATABASE_URL
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set")
    if database_url == os.environ.get("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL must differ from DATABASE_URL")
    _run_alembic("upgrade", "head")
    return database_url


@pytest.fixture(scope="session")
def seeded_session_factory(test_database_url: str):
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    with session_factory() as session:
        load_fixtures(FIXTURES_DIR, session)
        session.commit()

    try:
        yield session_factory
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def network_analysis_run(seeded_session_factory, tmp_path_factory):
    with seeded_session_factory() as session:
        session.merge(
            TaxonomyVersion(
                version="api-0.2.0",
                source_hash="a" * 64,
                source_path="data/taxonomy.json",
                is_current=False,
            )
        )
        session.merge(
            QualityRuleCatalogue(
                version="0.1.0",
                schema_version=1,
                source_hash="c" * 64,
                source_path="data/quality/rules-v0.1.0.json",
            )
        )
        session.flush()
        normalization = NormalizationRun(
            id=uuid.uuid4(),
            dataset_version="api-fixture",
            manifest_sha256="b" * 64,
            seed_list_version="0.2.0",
            taxonomy_version="api-0.2.0",
            tag_map_version="0.1.0",
            overrides_version="0.1.0",
            status="completed",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            code_version="test",
        )
        session.add(normalization)
        session.flush()
        quality = QualityRun(
            id=uuid.uuid4(),
            normalization_run_id=normalization.id,
            dataset_version="api-fixture",
            taxonomy_version="api-0.2.0",
            catalogue_version="0.1.0",
            code_version="test",
            status="completed_with_findings",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            parameters={},
            counters={},
        )
        session.add(quality)
        session.flush()
        inputs = NetworkInputs(
            normalization_run=normalization,
            quality_run=quality,
            taxonomy_path=Path(__file__).resolve().parents[3] / "data" / "taxonomy.json",
            taxonomy_version="api-0.2.0",
        )
        data = load_network_data(session, quality_run=quality)
        album_layer = build_producer_album_layer(data)
        band_layer = build_producer_band_layer(data, album_layer)
        metrics = compute_metrics(data, album_layer, band_layer)
        parameters = {"top_k": 20, "roles": ["producer", "co-producer"]}
        version = analysis_version(
            inputs,
            graph_version=GRAPH_VERSION,
            code_version="test-api",
            parameters=parameters,
        )
        run = start_analysis_run(
            session,
            version=version,
            inputs=inputs,
            graph_version=GRAPH_VERSION,
            code_version="test-api",
            parameters=parameters,
        )
        persist_network_run(
            session,
            run=run,
            data=data,
            album_layer=album_layer,
            band_layer=band_layer,
            metrics=metrics,
        )
        report = write_network_report(
            tmp_path_factory.mktemp("api-network"),
            run=run,
            data=data,
            metrics=metrics,
        )
        run.report_path = str(report.report_path)
        session.commit()
        return run.id


@pytest.fixture(scope="session")
def api_client(seeded_session_factory):
    def override_get_db():
        with seeded_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
