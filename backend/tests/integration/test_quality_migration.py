from __future__ import annotations

from sqlalchemy import create_engine, inspect

QUALITY_TABLES = {
    "quality_rule_catalogue",
    "quality_rule",
    "quality_run",
    "quality_finding",
    "quality_exception",
    "quality_metric",
}


def test_quality_tables_columns_and_constraints_exist(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        assert QUALITY_TABLES <= set(inspector.get_table_names())

        run_columns = {column["name"] for column in inspector.get_columns("quality_run")}
        assert {
            "normalization_run_id",
            "dataset_version",
            "taxonomy_version",
            "catalogue_version",
            "code_version",
            "status",
            "started_at",
            "finished_at",
            "parameters",
            "counters",
            "report_path",
        } <= run_columns

        finding_columns = {column["name"] for column in inspector.get_columns("quality_finding")}
        assert {
            "quality_run_id",
            "rule_id",
            "finding_key",
            "entity_type",
            "entity_mbid",
            "severity",
            "status",
            "observed_value",
            "expected_value",
            "details",
        } <= finding_columns

        metric_columns = {column["name"] for column in inspector.get_columns("quality_metric")}
        assert {
            "metric_code",
            "dimension",
            "scope_type",
            "scope_key",
            "numerator",
            "denominator",
            "value",
            "unit",
            "missing_count",
        } <= metric_columns

        run_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("quality_run")
        }
        assert {"ck_quality_run_status", "ck_quality_run_finished_at"} <= run_checks

        exception_checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("quality_exception")
        }
        assert "ck_quality_exception_status" in exception_checks

        finding_fks = {
            (fk["referred_table"], fk["options"].get("ondelete"))
            for fk in inspector.get_foreign_keys("quality_finding")
        }
        assert ("quality_run", "RESTRICT") in finding_fks
        assert ("quality_rule", "RESTRICT") in finding_fks
    finally:
        engine.dispose()


def test_quality_migration_does_not_remove_normalization_tables(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {
            "normalization_run",
            "release_group_subgenre",
            "artist_subgenre_classification",
            "dataset_membership",
        } <= tables
    finally:
        engine.dispose()
