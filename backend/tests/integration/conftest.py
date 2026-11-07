from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hmde.db.session import get_db
from hmde.main import app
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
