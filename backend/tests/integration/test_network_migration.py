from __future__ import annotations

from sqlalchemy import create_engine, inspect

ANALYTICS_TABLES = {
    "analysis_run",
    "graph_node",
    "graph_edge",
    "node_metric",
    "producer_metric",
    "temporal_metric",
    "community",
    "community_membership",
}


def test_analytics_tables_columns_and_constraints_exist(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        assert ANALYTICS_TABLES <= set(inspector.get_table_names())

        run_columns = {column["name"] for column in inspector.get_columns("analysis_run")}
        assert {
            "analysis_version",
            "normalization_run_id",
            "quality_run_id",
            "dataset_version",
            "taxonomy_version",
            "graph_version",
            "code_version",
            "status",
            "started_at",
            "finished_at",
            "parameters",
            "counters",
            "report_path",
        } <= run_columns

        edge_columns = {column["name"] for column in inspector.get_columns("graph_edge")}
        assert {
            "layer_code",
            "source_node_id",
            "target_node_id",
            "role_code",
            "weight",
            "supporting_recordings",
            "album_recordings",
            "support_ratio",
            "scope_mix",
            "evidence",
        } <= edge_columns

        edge_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("graph_edge")
        }
        assert {
            "ck_graph_edge_layer",
            "ck_graph_edge_weight",
            "ck_graph_edge_support_ratio",
            "ck_graph_edge_no_self_loop",
        } <= edge_checks

        node_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("graph_node")
        }
        assert "ck_graph_node_type" in node_checks

        run_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("analysis_run")
        }
        assert {"ck_analysis_run_status", "ck_analysis_run_finished_at"} <= run_checks

        edge_fks = {
            (fk["referred_table"], fk["options"].get("ondelete"))
            for fk in inspector.get_foreign_keys("graph_edge")
        }
        assert ("analysis_run", "RESTRICT") in edge_fks
        assert ("graph_node", "RESTRICT") in edge_fks
    finally:
        engine.dispose()


def test_analytics_migration_keeps_canonical_tables(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {
            "artist",
            "release_group",
            "credit",
            "normalization_run",
            "quality_run",
        } <= tables
    finally:
        engine.dispose()
