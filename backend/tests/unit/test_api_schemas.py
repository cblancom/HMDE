from __future__ import annotations

import uuid

from hmde.schemas.api import ProducerGraphLimits, ProducerGraphMeta


def test_producer_graph_meta_exposes_limits_and_run_versions() -> None:
    meta = ProducerGraphMeta(
        view="bands",
        analysis_run_id=uuid.uuid4(),
        analysis_version="net-test",
        dataset_version="mb-test",
        taxonomy_version="0.2.0",
        graph_version="0.1.0",
        truncated=False,
        limits=ProducerGraphLimits(limit=20, depth=1, max_nodes=500, max_edges=2000),
    )
    assert meta.view == "bands"
    assert meta.limits.max_nodes == 500
