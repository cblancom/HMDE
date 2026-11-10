from __future__ import annotations

import uuid
from datetime import UTC, datetime

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
    TemporalMetric,
)
from hmde.network import GRAPH_VERSION
from hmde.network.graph import build_producer_album_layer, build_producer_band_layer
from hmde.network.inputs import NetworkInputs
from hmde.network.loader import load_network_data
from hmde.network.metrics import compute_metrics
from hmde.network.persistence import (
    analysis_version,
    find_completed_run,
    persist_network_run,
    start_analysis_run,
)


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


def _build(session, *_):
    normalization = session.scalar(
        select(NormalizationRun).order_by(NormalizationRun.started_at.desc())
    )
    quality = session.scalar(select(QualityRun).order_by(QualityRun.started_at.desc()))
    inputs = NetworkInputs(
        normalization_run=normalization,
        quality_run=quality,
        taxonomy_path=__import__("pathlib").Path(__file__).resolve().parents[3]
        / "data"
        / "taxonomy.json",
        taxonomy_version="0.2.0",
    )
    data = load_network_data(session, quality_run=quality)
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    metrics = compute_metrics(data, album_layer, band_layer)
    return inputs, data, album_layer, band_layer, metrics


def test_persist_network_run_and_reuse_version(seeded_session_factory) -> None:
    with seeded_session_factory() as session:
        _setup(session)
        inputs, data, album_layer, band_layer, metrics = _build(session)
        parameters = {"top_k": 20, "roles": ["producer", "co-producer"]}
        version = analysis_version(
            inputs,
            graph_version=GRAPH_VERSION,
            code_version="test",
            parameters=parameters,
        )
        first = start_analysis_run(
            session,
            version=version,
            inputs=inputs,
            graph_version=GRAPH_VERSION,
            code_version="test",
            parameters=parameters,
        )
        persist_network_run(
            session,
            run=first,
            data=data,
            album_layer=album_layer,
            band_layer=band_layer,
            metrics=metrics,
        )
        assert session.scalar(select(func.count()).select_from(GraphNode)) > 0
        assert session.scalar(select(func.count()).select_from(GraphEdge)) > 0
        assert session.scalar(select(func.count()).select_from(TemporalMetric)) > 0
        assert session.scalar(select(func.count()).select_from(Community)) > 0
        assert first.status in {"completed", "completed_with_limitations"}
        found = find_completed_run(session, version=version)
        assert found is not None
        assert found.id == first.id
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1
        session.rollback()
