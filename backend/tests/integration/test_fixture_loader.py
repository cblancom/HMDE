from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import (
    Artist,
    ArtistSubgenre,
    Credit,
    ExternalId,
    FixtureLoad,
    Recording,
    RecordingRelease,
    Release,
    ReleaseGroup,
    Role,
    SourceRecord,
    Subgenre,
)
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


def _counts(session: Session) -> dict[str, int]:
    models = {
        "artists": Artist,
        "artist_subgenres": ArtistSubgenre,
        "credits": Credit,
        "external_ids": ExternalId,
        "fixture_loads": FixtureLoad,
        "recording_releases": RecordingRelease,
        "recordings": Recording,
        "release_groups": ReleaseGroup,
        "releases": Release,
        "roles": Role,
        "source_records": SourceRecord,
        "subgenres": Subgenre,
    }
    return {
        name: session.scalar(select(func.count()).select_from(model)) or 0
        for name, model in models.items()
    }


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")
def test_fixture_loader_is_idempotent() -> None:
    if TEST_DATABASE_URL == os.environ.get("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL must differ from DATABASE_URL")

    _run_alembic("upgrade", "head")
    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    try:
        with session_factory() as session:
            first_result = load_fixtures(FIXTURES_DIR, session)
            session.commit()

        with session_factory() as session:
            first_counts = _counts(session)

        with session_factory() as session:
            second_result = load_fixtures(FIXTURES_DIR, session)
            session.commit()

        with session_factory() as session:
            second_counts = _counts(session)

        manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))

        assert first_result == second_result
        assert first_counts["artists"] == manifest["artist_count"]
        assert first_counts["artist_subgenres"] == manifest["artist_subgenre_count"]
        assert first_counts["credits"] == manifest["credit_count"]
        assert first_counts["external_ids"] == manifest["external_id_count"]
        assert first_counts["recording_releases"] == manifest["recording_release_count"]
        assert first_counts["recordings"] == manifest["recording_count"]
        assert first_counts["release_groups"] == manifest["release_group_count"]
        assert first_counts["releases"] == manifest["release_count"]
        assert first_counts["roles"] == manifest["role_count"]
        assert first_counts["source_records"] == manifest["source_record_count"]
        assert first_counts["subgenres"] == manifest["subgenre_count"]
        assert first_counts["fixture_loads"] == 1
        assert second_counts == {**first_counts, "fixture_loads": 2}
    finally:
        engine.dispose()
