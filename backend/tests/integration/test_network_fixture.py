from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from hmde.models import (
    AnalysisRun,
    Community,
    GraphEdge,
    GraphNode,
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


def test_fixture_run_writes_complete_network_report(seeded_session_factory, tmp_path: Path) -> None:
    with seeded_session_factory() as session:
        normalization, quality = _setup(session)
        options = NetworkOptions(
            normalization_run=normalization.id,
            quality_run=quality.id,
            taxonomy=DATA / "taxonomy.json",
            output=tmp_path / "network",
            top_k=20,
            decade=None,
            subgenre=None,
            bands=(),
        )
        result = execute_network(session, options, code_version="test")
        assert result.report_path is not None
        report = json.loads(result.report_path.read_text(encoding="utf-8"))
        assert report["analysis_version"] == result.analysis_version
        assert report["graph_counts"]["producer_album"]["nodes"] > 0
        assert report["top_albums"]
        assert report["quality"]["active_exceptions"] >= 0
        assert (result.report_path.parent / "report.md").is_file()
        assert (result.report_path.parent / "manifest.json").is_file()
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1
        assert session.scalar(select(func.count()).select_from(GraphNode)) > 0
        assert session.scalar(select(func.count()).select_from(GraphEdge)) > 0
        assert session.scalar(select(func.count()).select_from(Community)) > 0
        session.rollback()
