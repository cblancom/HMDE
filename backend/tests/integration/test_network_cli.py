from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from hmde.models import NormalizationRun, QualityRuleCatalogue, QualityRun, TaxonomyVersion
from hmde.network.cli import NetworkOptions, execute_network

DATA = Path(__file__).resolve().parents[3] / "data"


def _setup(session):
    session.merge(
        TaxonomyVersion(
            version="0.2.0",
            source_hash="a" * 64,
            source_path="data/taxonomy.json",
            is_current=True,
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
        dataset_version="fixture-test",
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
    quality = QualityRun(
        id=uuid.uuid4(),
        normalization_run_id=normalization.id,
        dataset_version="fixture-test",
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


def test_execute_network_writes_report_and_reuses_run(
    seeded_session_factory, tmp_path: Path
) -> None:
    with seeded_session_factory() as session:
        normalization, quality = _setup(session)
        options = NetworkOptions(
            normalization_run=normalization.id,
            quality_run=quality.id,
            taxonomy=DATA / "taxonomy.json",
            output=tmp_path / "network",
            top_k=10,
            decade=None,
            subgenre=None,
            bands=(),
        )
        first = execute_network(session, options, code_version="test")
        second = execute_network(session, options, code_version="test")
        assert first.report_path is not None
        assert first.report_path.is_file()
        assert first.markdown_path is not None
        assert first.markdown_path.is_file()
        assert second.reused is True
        assert second.run_id == first.run_id
        assert first.counters["graphs"]["producer_album"]["nodes"] > 0
        session.rollback()
