from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hmde.api.dependencies import resolve_analysis_run
from hmde.models import (
    AnalysisRun,
    NormalizationRun,
    QualityRuleCatalogue,
    QualityRun,
    TaxonomyVersion,
)


def _run(session, *, status: str = "completed", finished: datetime | None = None) -> AnalysisRun:
    session.merge(
        TaxonomyVersion(
            version="api-input-taxonomy",
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
        dataset_version="api-test",
        manifest_sha256="b" * 64,
        seed_list_version="0.2.0",
        taxonomy_version="api-input-taxonomy",
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
        dataset_version="api-test",
        taxonomy_version="api-input-taxonomy",
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
    run = AnalysisRun(
        id=uuid.uuid4(),
        analysis_version=f"net-{uuid.uuid4().hex[:16]}",
        normalization_run_id=normalization.id,
        quality_run_id=quality.id,
        dataset_version="api-test",
        taxonomy_version="api-input-taxonomy",
        graph_version="0.1.0",
        code_version="test",
        status=status,
        started_at=datetime.now(UTC),
        finished_at=finished
        if finished is not None
        else (datetime.now(UTC) if status != "running" else None),
        parameters={},
        counters={},
    )
    session.add(run)
    session.flush()
    return run


def test_resolves_latest_completed_run_and_explicit_run(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with factory() as session:
            older = _run(session, finished=datetime(2030, 1, 1, tzinfo=UTC))
            newer = _run(
                session,
                status="completed_with_limitations",
                finished=datetime(2030, 1, 2, tzinfo=UTC),
            )
            assert resolve_analysis_run(session).id == newer.id
            assert resolve_analysis_run(session, older.id).id == older.id
            session.rollback()
    finally:
        engine.dispose()


def test_explicit_missing_and_nonterminal_runs_fail(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with factory() as session:
            run = _run(session, status="running")
            with pytest.raises(HTTPException) as missing:
                resolve_analysis_run(session, uuid.uuid4())
            assert missing.value.status_code == 404
            with pytest.raises(HTTPException) as nonterminal:
                resolve_analysis_run(session, run.id)
            assert nonterminal.value.status_code == 409
            session.rollback()
    finally:
        engine.dispose()
