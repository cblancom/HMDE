from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

NORMALIZATION_TABLES = {
    "taxonomy_version",
    "taxonomy_node",
    "normalization_run",
    "normalization_issue",
    "normalization_issue_action",
    "release_group_subgenre",
    "artist_subgenre_classification",
    "dataset_membership",
}


def test_normalization_tables_columns_and_constraints_exist(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        assert NORMALIZATION_TABLES <= tables

        run_columns = {column["name"] for column in inspector.get_columns("normalization_run")}
        assert {
            "dataset_version",
            "manifest_sha256",
            "seed_list_version",
            "taxonomy_version",
            "tag_map_version",
            "overrides_version",
            "status",
            "started_at",
            "finished_at",
            "code_version",
            "parameters",
            "counters",
            "report_path",
        } <= run_columns

        issue_columns = {column["name"] for column in inspector.get_columns("normalization_issue")}
        assert {
            "issue_key",
            "normalization_run_id",
            "entity_type",
            "entity_mbid",
            "taxonomy_version",
            "issue_type",
            "severity",
            "status",
            "reason",
            "evidence",
            "created_at",
            "updated_at",
        } <= issue_columns

        membership_columns = {
            column["name"] for column in inspector.get_columns("dataset_membership")
        }
        assert {
            "dataset_version",
            "artist_id",
            "seed_list_version",
            "batch_id",
            "lifecycle",
            "added_in_version",
            "retired_in_version",
            "replaced_by_artist_id",
            "source_record_id",
        } <= membership_columns

        status_checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("normalization_run")
        }
        assert {
            "ck_normalization_run_status",
            "ck_normalization_run_finished_at",
        } <= status_checks

        issue_checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("normalization_issue")
        }
        assert {
            "ck_normalization_issue_severity",
            "ck_normalization_issue_status",
        } <= issue_checks

        membership_checks = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("dataset_membership")
        }
        assert {
            "ck_dataset_membership_lifecycle",
            "ck_dataset_membership_retired",
        } <= membership_checks
    finally:
        engine.dispose()


def test_source_record_and_artist_subgenre_are_extended(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        source_columns = {
            column["name"]: column for column in inspector.get_columns("source_record")
        }
        assert {
            "raw_response_id",
            "http_status",
            "api_version",
            "dataset_version",
            "ingest_run_id",
        } <= set(source_columns)
        assert source_columns["fixture_version"]["nullable"] is True

        artist_subgenre_columns = {
            column["name"] for column in inspector.get_columns("artist_subgenre")
        }
        assert {
            "taxonomy_version",
            "status",
            "mapping_rule",
            "updated_at",
        } <= artist_subgenre_columns

        artist_subgenre_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("artist_subgenre")
        }
        assert "ck_artist_subgenre_status" in artist_subgenre_checks
    finally:
        engine.dispose()


def test_assistant_producer_role_is_seeded(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            value = connection.scalar(
                text("SELECT category FROM role WHERE code = 'assistant-producer'")
            )
        assert value == "extended"
    finally:
        engine.dispose()
