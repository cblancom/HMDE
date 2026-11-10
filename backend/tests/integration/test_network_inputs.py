from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hmde.models import NormalizationRun, QualityRuleCatalogue, QualityRun, TaxonomyVersion
from hmde.network.errors import NetworkInputError
from hmde.network.inputs import load_network_inputs

DATA = Path(__file__).resolve().parents[3] / "data"
TAXONOMY = DATA / "taxonomy.json"


def _runs(session):
    session.merge(
        TaxonomyVersion(
            version="0.2.0",
            source_hash="a" * 64,
            source_path="data/taxonomy.json",
            is_current=True,
        )
    )
    session.flush()
    normalization = NormalizationRun(
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
    session.add(normalization)
    session.flush()
    session.merge(
        QualityRuleCatalogue(
            version="0.1.0",
            schema_version=1,
            source_hash="c" * 64,
            source_path="data/quality/rules-v0.1.0.json",
        )
    )
    session.flush()
    quality = QualityRun(
        id=uuid.uuid4(),
        normalization_run_id=normalization.id,
        dataset_version="mb-test",
        taxonomy_version="0.2.0",
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
    return normalization, quality


def test_valid_inputs_load(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            normalization, quality = _runs(session)
            inputs = load_network_inputs(
                session,
                normalization_run_id=normalization.id,
                quality_run_id=quality.id,
                taxonomy_path=TAXONOMY,
            )
            assert inputs.normalization_run.id == normalization.id
            assert inputs.quality_run.id == quality.id
            assert inputs.taxonomy_version == "0.2.0"
            session.rollback()
    finally:
        engine.dispose()


def test_quality_run_mismatch_rejected(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            normalization, quality = _runs(session)
            quality.dataset_version = "different-dataset"
            session.flush()
            with pytest.raises(NetworkInputError, match="dataset versions differ"):
                load_network_inputs(
                    session,
                    normalization_run_id=normalization.id,
                    quality_run_id=quality.id,
                    taxonomy_path=TAXONOMY,
                )
            session.rollback()
    finally:
        engine.dispose()


def test_taxonomy_mismatch_rejected(test_database_url: str, tmp_path: Path) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            normalization, quality = _runs(session)
            taxonomy = tmp_path / "taxonomy.json"
            taxonomy.write_text('{"version": "9.9.9"}', encoding="utf-8")
            with pytest.raises(NetworkInputError, match="taxonomy version mismatch"):
                load_network_inputs(
                    session,
                    normalization_run_id=normalization.id,
                    quality_run_id=quality.id,
                    taxonomy_path=taxonomy,
                )
            session.rollback()
    finally:
        engine.dispose()


def test_non_terminal_normalization_rejected(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            normalization, quality = _runs(session)
            normalization.status = "running"
            normalization.finished_at = None
            session.flush()
            with pytest.raises(NetworkInputError, match="not terminal"):
                load_network_inputs(
                    session,
                    normalization_run_id=normalization.id,
                    quality_run_id=quality.id,
                    taxonomy_path=TAXONOMY,
                )
            session.rollback()
    finally:
        engine.dispose()
