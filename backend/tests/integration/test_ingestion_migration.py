from __future__ import annotations

from sqlalchemy import create_engine, inspect

CANONICAL_TABLES = {
    "artist",
    "artist_subgenre",
    "credit",
    "external_id",
    "fixture_load",
    "recording",
    "recording_release",
    "release",
    "release_group",
    "role",
    "source_record",
    "subgenre",
}


def test_ingestion_tables_and_constraints_exist(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        assert CANONICAL_TABLES <= tables
        assert {"ingest_run", "raw_response", "ingest_error"} <= tables

        ingest_run_columns = {column["name"] for column in inspector.get_columns("ingest_run")}
        assert {
            "id",
            "seed_list_version",
            "dataset_version",
            "status",
            "started_at",
            "finished_at",
            "code_version",
            "parameters",
            "counters",
            "output_path",
            "source_snapshot_at",
        } <= ingest_run_columns

        raw_response_columns = {column["name"] for column in inspector.get_columns("raw_response")}
        assert {
            "id",
            "first_ingest_run_id",
            "source",
            "source_entity_type",
            "external_id",
            "request_key",
            "request_url",
            "request_params",
            "fetched_at",
            "http_status",
            "payload_hash",
            "raw_path",
            "license",
            "api_version",
        } <= raw_response_columns

        ingest_error_columns = {column["name"] for column in inspector.get_columns("ingest_error")}
        assert {
            "id",
            "ingest_run_id",
            "band_mbid",
            "phase",
            "request_key",
            "error_type",
            "message",
            "attempts",
            "occurred_at",
        } <= ingest_error_columns
    finally:
        engine.dispose()


def test_ingestion_constraints_and_indexes_exist(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)

        ingest_run_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("ingest_run")
        }
        assert {"ck_ingest_run_status", "ck_ingest_run_finished_at"} <= ingest_run_checks

        raw_response_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("raw_response")
        }
        assert "ck_raw_response_http_status" in raw_response_checks

        raw_response_uniques = {
            constraint["name"] for constraint in inspector.get_unique_constraints("raw_response")
        }
        assert "uq_raw_response_request_payload" in raw_response_uniques

        ingest_error_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("ingest_error")
        }
        assert "ck_ingest_error_attempts" in ingest_error_checks

        ingest_run_indexes = {index["name"] for index in inspector.get_indexes("ingest_run")}
        assert {"ix_ingest_run_status", "ix_ingest_run_started_at"} <= ingest_run_indexes

        raw_response_indexes = {index["name"] for index in inspector.get_indexes("raw_response")}
        assert {
            "ix_raw_response_request_key",
            "ix_raw_response_source_external_id",
            "ix_raw_response_first_ingest_run_id",
        } <= raw_response_indexes

        ingest_error_indexes = {index["name"] for index in inspector.get_indexes("ingest_error")}
        assert {
            "ix_ingest_error_ingest_run_id",
            "ix_ingest_error_band_mbid",
        } <= ingest_error_indexes

        raw_response_fks = {
            (fk["referred_table"], fk["options"].get("ondelete"))
            for fk in inspector.get_foreign_keys("raw_response")
        }
        assert ("ingest_run", "RESTRICT") in raw_response_fks

        ingest_error_fks = {
            (fk["referred_table"], fk["options"].get("ondelete"))
            for fk in inspector.get_foreign_keys("ingest_error")
        }
        assert ("ingest_run", "CASCADE") in ingest_error_fks
    finally:
        engine.dispose()
