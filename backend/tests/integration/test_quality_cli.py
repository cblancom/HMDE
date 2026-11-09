from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from hmde.models import NormalizationRun, QualityFinding, QualityMetric, QualityRun, TaxonomyVersion
from hmde.quality.cli import QualityOptions, execute_quality

DATA = Path(__file__).resolve().parents[3] / "data"
RULES = DATA / "quality" / "rules-v0.1.0.json"
EXCEPTIONS = DATA / "quality" / "exceptions-v0.1.0.json"


def _normalization_run(session) -> NormalizationRun:
    session.add(
        TaxonomyVersion(
            version="0.2.0",
            source_hash="a" * 64,
            source_path="data/taxonomy.json",
            is_current=True,
        )
    )
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


def test_execute_quality_writes_report_and_tables(
    test_database_url: str,
    tmp_path: Path,
) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            normalization = _normalization_run(session)
            result = execute_quality(
                session,
                QualityOptions(
                    normalization_run=normalization.id,
                    rules=RULES,
                    exceptions=EXCEPTIONS,
                    output=tmp_path / "quality",
                    strict=False,
                ),
                code_version="test",
            )

            assert result.status == "completed_with_findings"
            assert result.report_path is not None
            report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
            assert report["status"] == "completed_with_findings"
            assert report["gate"]["blocking_unexcepted"] > 0
            assert session.get(QualityRun, result.run_id) is not None
            assert session.scalar(select(func.count()).select_from(QualityFinding)) > 0
            assert session.scalar(select(func.count()).select_from(QualityMetric)) > 0
            assert report["exceptions"]
            session.rollback()
    finally:
        engine.dispose()
