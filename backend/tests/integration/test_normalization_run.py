from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from hmde.models import Artist, NormalizationRun
from hmde.normalization.inputs import validate_inputs
from hmde.normalization.pipeline import NormalizationRunner
from hmde.normalization.taxonomy import sync_taxonomy

DATA = Path(__file__).resolve().parents[3] / "data"
MINI_DATASET = Path(__file__).resolve().parents[1] / "fixtures" / "normalization" / "mini-dataset"
TAXONOMY = DATA / "taxonomy.json"
TAG_MAP = DATA / "classifications" / "tag-map-v0.1.0.json"
OVERRIDES = DATA / "classifications" / "manual-overrides-v0.1.0.json"


def test_dry_run_validates_and_writes_only_run_metadata(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        inputs = validate_inputs(
            MINI_DATASET,
            taxonomy_path=TAXONOMY,
            tag_map_path=TAG_MAP,
            overrides_path=OVERRIDES,
        )
        with session_factory() as session:
            sync_taxonomy(session, TAXONOMY)
            before_artists = session.scalar(select(func.count()).select_from(Artist))
            result = NormalizationRunner(
                session,
                inputs,
                code_version="test-version",
            ).dry_run()

            run = session.get(NormalizationRun, result.run_id)
            assert run is not None
            assert result.dry_run is True
            assert result.status == "completed"
            assert run.status == "completed"
            assert run.finished_at is not None
            assert run.parameters["mode"] == "dry-run"
            assert run.counters["bands"] == 1
            assert run.counters["release_groups"] == 1
            assert session.scalar(select(func.count()).select_from(Artist)) == before_artists
            session.rollback()
    finally:
        engine.dispose()


def test_run_requires_persisted_taxonomy(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        inputs = validate_inputs(
            MINI_DATASET,
            taxonomy_path=TAXONOMY,
            tag_map_path=TAG_MAP,
            overrides_path=OVERRIDES,
        )
        with session_factory() as session:
            try:
                NormalizationRunner(session, inputs, code_version="test").dry_run()
            except Exception as exc:
                assert "taxonomy version is not persisted" in str(exc)
            else:
                raise AssertionError("expected missing taxonomy to fail")
            session.rollback()
    finally:
        engine.dispose()
