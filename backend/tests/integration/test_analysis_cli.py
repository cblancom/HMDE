from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hmde.analytics.cli import AnalysisOptions, execute_analysis
from hmde.models import NormalizationRun, QualityRuleCatalogue, QualityRun, TaxonomyVersion

DATA = Path(__file__).resolve().parents[3] / "data"
TAXONOMY = DATA / "taxonomy.json"
CATALOGUE = DATA / "metrics" / "catalogue-v0.1.0.json"


def _setup(session):
    session.add(
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


def test_execute_analysis_writes_versioned_report(test_database_url: str, tmp_path: Path) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            normalization, quality = _setup(session)
            options = AnalysisOptions(
                normalization_run=normalization.id,
                quality_run=quality.id,
                taxonomy=TAXONOMY,
                catalogue=CATALOGUE,
                output=tmp_path / "analysis",
            )
            first = execute_analysis(session, options, code_version="test")
            second = execute_analysis(session, options, code_version="test")

            assert first.analysis_version == second.analysis_version
            assert first.report_path.is_file()
            assert first.markdown_path.is_file()
            assert (first.report_path.parent / "manifest.json").is_file()
            assert first.metric_count > 0
            data = json.loads(first.report_path.read_text(encoding="utf-8"))
            assert data["analysis_version"] == first.analysis_version
            assert data["dataset_version"] == "mb-test"
            assert data["metrics"]
            session.rollback()
    finally:
        engine.dispose()
