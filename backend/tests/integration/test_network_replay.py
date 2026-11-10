from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from hmde.models import (
    AnalysisRun,
    NormalizationRun,
    QualityRuleCatalogue,
    QualityRun,
    TaxonomyVersion,
)
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


def _options(normalization, quality, output: Path, *, top_k: int = 20) -> NetworkOptions:
    return NetworkOptions(
        normalization_run=normalization.id,
        quality_run=quality.id,
        taxonomy=DATA / "taxonomy.json",
        output=output,
        top_k=top_k,
        decade=None,
        subgenre=None,
        bands=(),
    )


def test_replay_reuses_and_changed_inputs_create_new_versions(
    seeded_session_factory, tmp_path: Path
) -> None:
    with seeded_session_factory() as session:
        normalization, quality = _setup(session)
        output = tmp_path / "network"
        first = execute_network(
            session, _options(normalization, quality, output), code_version="test"
        )
        second = execute_network(
            session, _options(normalization, quality, output), code_version="test"
        )
        assert second.reused is True
        assert second.run_id == first.run_id
        first_report = first.report_path
        assert first_report is not None and first_report.is_file()

        changed_top_k = execute_network(
            session,
            _options(normalization, quality, output, top_k=5),
            code_version="test",
        )
        assert changed_top_k.reused is False
        assert changed_top_k.analysis_version != first.analysis_version

        normalization.dataset_version = "fixture-test-v2"
        quality.dataset_version = "fixture-test-v2"
        session.flush()
        changed_dataset = execute_network(
            session, _options(normalization, quality, output), code_version="test"
        )
        assert changed_dataset.reused is False
        assert changed_dataset.analysis_version != first.analysis_version
        assert first_report.is_file()
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 3
        session.rollback()
