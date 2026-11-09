from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from hmde.models import NormalizationRun, QualityRun, TaxonomyVersion
from hmde.quality.errors import QualityInputError
from hmde.quality.inputs import load_quality_inputs
from hmde.quality.runner import finish_quality_run, start_quality_run

DATA = Path(__file__).resolve().parents[3] / "data"
CATALOGUE = DATA / "quality" / "rules-v0.1.0.json"
EXCEPTIONS = DATA / "quality" / "exceptions-v0.1.0.json"


def _normalization_run(session) -> NormalizationRun:
    taxonomy = TaxonomyVersion(
        version="0.2.0",
        source_hash="a" * 64,
        source_path="data/taxonomy.json",
        is_current=True,
    )
    session.merge(taxonomy)
    session.flush()
    run = NormalizationRun(
        id=uuid.uuid4(),
        dataset_version="mb-test",
        manifest_sha256="b" * 64,
        seed_list_version="0.2.0",
        taxonomy_version="0.2.0",
        tag_map_version="0.1.0",
        overrides_version="0.1.0",
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        code_version="test",
    )
    session.add(run)
    session.flush()
    return run


def test_quality_run_uses_selected_normalization_run(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            normalization = _normalization_run(session)
            inputs = load_quality_inputs(
                session,
                normalization_run_id=normalization.id,
                rules_path=CATALOGUE,
                exceptions_path=EXCEPTIONS,
            )
            run, catalogue = start_quality_run(
                session,
                inputs,
                code_version="test",
                modes={"mode": "test"},
            )

            assert run.status == "running"
            assert run.dataset_version == "mb-test"
            assert run.taxonomy_version == "0.2.0"
            assert run.catalogue_version == "0.1.0"
            assert catalogue.version == "0.1.0"
            assert session.scalar(select(func.count()).select_from(QualityRun)) == 1

            finish_quality_run(
                session,
                run,
                status="completed",
                counters={"rules": 20},
            )
            assert run.status == "completed"
            assert run.finished_at is not None
            assert run.counters["rules"] == 20
            session.rollback()
    finally:
        engine.dispose()


def test_quality_inputs_reject_missing_run(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            with pytest.raises(QualityInputError, match="does not exist"):
                load_quality_inputs(
                    session,
                    normalization_run_id=uuid.uuid4(),
                    rules_path=CATALOGUE,
                    exceptions_path=EXCEPTIONS,
                )
    finally:
        engine.dispose()
