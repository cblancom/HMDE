from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from hmde.models import Artist, Credit, NormalizationRun, ReleaseGroup, TaxonomyVersion
from hmde.quality.cli import QualityOptions, execute_quality

DATA = Path(__file__).resolve().parents[3] / "data"
RULES = DATA / "quality" / "rules-v0.1.0.json"
EXCEPTIONS = DATA / "quality" / "exceptions-v0.1.0.json"


def test_quality_fixture_run_does_not_mutate_canonical_data(
    test_database_url: str,
    tmp_path: Path,
) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
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
            before = {
                "artists": session.scalar(select(func.count()).select_from(Artist)),
                "release_groups": session.scalar(select(func.count()).select_from(ReleaseGroup)),
                "credits": session.scalar(select(func.count()).select_from(Credit)),
            }
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
            after = {
                "artists": session.scalar(select(func.count()).select_from(Artist)),
                "release_groups": session.scalar(select(func.count()).select_from(ReleaseGroup)),
                "credits": session.scalar(select(func.count()).select_from(Credit)),
            }
            assert result.status == "completed_with_findings"
            assert before == after
            session.rollback()
    finally:
        engine.dispose()
