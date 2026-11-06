from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from hmde.db.session import get_db
from hmde.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture
def real_db_session() -> Iterator[Session]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    if TEST_DATABASE_URL == os.environ.get("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL must differ from DATABASE_URL")

    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_health_against_real_database(real_db_session: Session) -> None:
    def override_get_db() -> Iterator[Session]:
        yield real_db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
