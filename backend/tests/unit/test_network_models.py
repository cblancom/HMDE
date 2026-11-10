from __future__ import annotations

from hmde.models import (
    AnalysisRun,
    Community,
    CommunityMembership,
    GraphEdge,
    GraphNode,
    NodeMetric,
    ProducerMetric,
    TemporalMetric,
)


def test_analytics_tables_and_checks_are_registered() -> None:
    assert AnalysisRun.__tablename__ == "analysis_run"
    assert GraphNode.__tablename__ == "graph_node"
    assert GraphEdge.__tablename__ == "graph_edge"
    assert NodeMetric.__tablename__ == "node_metric"
    assert ProducerMetric.__tablename__ == "producer_metric"
    assert TemporalMetric.__tablename__ == "temporal_metric"
    assert Community.__tablename__ == "community"
    assert CommunityMembership.__tablename__ == "community_membership"

    edge_checks = {
        constraint.name for constraint in GraphEdge.__table__.constraints if constraint.name
    }
    assert {
        "ck_graph_edge_layer",
        "ck_graph_edge_weight",
        "ck_graph_edge_support_ratio",
        "ck_graph_edge_no_self_loop",
    } <= edge_checks
    node_checks = {
        constraint.name for constraint in GraphNode.__table__.constraints if constraint.name
    }
    assert "ck_graph_node_type" in node_checks
    run_checks = {
        constraint.name for constraint in AnalysisRun.__table__.constraints if constraint.name
    }
    assert {"ck_analysis_run_status", "ck_analysis_run_finished_at"} <= run_checks
