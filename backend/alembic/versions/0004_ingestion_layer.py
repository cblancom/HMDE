"""ingestion layer

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seed_list_version", sa.String(length=50), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=True),
        sa.Column(
            "status", sa.String(length=30), server_default=sa.text("'running'"), nullable=False
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("code_version", sa.String(length=100), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "counters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_errors', 'failed')",
            name="ck_ingest_run_status",
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_ingest_run_finished_at",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingest_run_status", "ingest_run", ["status"], unique=False)
    op.create_index("ix_ingest_run_started_at", "ingest_run", ["started_at"], unique=False)

    op.create_table(
        "raw_response",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_ingest_run_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_entity_type", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("request_key", sa.String(length=64), nullable=False),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column(
            "request_params",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_path", sa.Text(), nullable=False),
        sa.Column("license", sa.String(length=100), nullable=False),
        sa.Column("api_version", sa.String(length=50), nullable=False),
        sa.CheckConstraint(
            "http_status BETWEEN 100 AND 599",
            name="ck_raw_response_http_status",
        ),
        sa.ForeignKeyConstraint(["first_ingest_run_id"], ["ingest_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "request_key",
            "payload_hash",
            name="uq_raw_response_request_payload",
        ),
    )
    op.create_index(
        "ix_raw_response_request_key",
        "raw_response",
        ["request_key"],
        unique=False,
    )
    op.create_index(
        "ix_raw_response_source_external_id",
        "raw_response",
        ["source", "external_id"],
        unique=False,
    )
    op.create_index(
        "ix_raw_response_first_ingest_run_id",
        "raw_response",
        ["first_ingest_run_id"],
        unique=False,
    )

    op.create_table(
        "ingest_error",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ingest_run_id", sa.Uuid(), nullable=False),
        sa.Column("band_mbid", sa.String(length=36), nullable=True),
        sa.Column("phase", sa.String(length=50), nullable=False),
        sa.Column("request_key", sa.String(length=64), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("attempts >= 1", name="ck_ingest_error_attempts"),
        sa.ForeignKeyConstraint(["ingest_run_id"], ["ingest_run.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingest_error_ingest_run_id",
        "ingest_error",
        ["ingest_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_ingest_error_band_mbid",
        "ingest_error",
        ["band_mbid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_error_band_mbid", table_name="ingest_error")
    op.drop_index("ix_ingest_error_ingest_run_id", table_name="ingest_error")
    op.drop_table("ingest_error")
    op.drop_index("ix_raw_response_first_ingest_run_id", table_name="raw_response")
    op.drop_index("ix_raw_response_source_external_id", table_name="raw_response")
    op.drop_index("ix_raw_response_request_key", table_name="raw_response")
    op.drop_table("raw_response")
    op.drop_index("ix_ingest_run_started_at", table_name="ingest_run")
    op.drop_index("ix_ingest_run_status", table_name="ingest_run")
    op.drop_table("ingest_run")
