from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from hmde.db.base import Base
from hmde.models import IngestError, IngestRun, RawResponse


def test_ingestion_tables_are_registered() -> None:
    assert IngestRun.__table__ is Base.metadata.tables["ingest_run"]
    assert RawResponse.__table__ is Base.metadata.tables["raw_response"]
    assert IngestError.__table__ is Base.metadata.tables["ingest_error"]


def test_ingest_run_columns_and_constraints() -> None:
    table = IngestRun.__table__
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

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
    } <= set(table.c.keys())
    assert {"ck_ingest_run_status", "ck_ingest_run_finished_at"} <= check_names


def test_raw_response_has_request_payload_uniqueness() -> None:
    table = RawResponse.__table__
    unique_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "uq_raw_response_request_payload" in unique_constraints
    assert "ck_raw_response_http_status" in check_names
    assert "first_ingest_run_id" in table.c
    assert "raw_path" in table.c
    assert "payload_hash" in table.c


def test_ingest_error_has_attempt_and_fk_constraints() -> None:
    table = IngestError.__table__
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_ingest_error_attempts" in check_names
    assert "ingest_run_id" in table.c
    assert "band_mbid" in table.c
    assert "request_key" in table.c
    assert table.c.ingest_run_id.foreign_keys
    fk = next(iter(table.c.ingest_run_id.foreign_keys))
    assert fk.target_fullname == "ingest_run.id"
    assert fk.ondelete == "CASCADE"
