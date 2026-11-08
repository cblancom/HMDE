"""normalization layer

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "taxonomy_version",
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'approved'"),
            nullable=False,
        ),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('approved', 'retired')",
            name="ck_taxonomy_version_status",
        ),
        sa.PrimaryKeyConstraint("version"),
    )
    op.create_index(
        "uq_taxonomy_version_current",
        "taxonomy_version",
        ["is_current"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "taxonomy_node",
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("parent_code", sa.String(length=50), nullable=True),
        sa.Column("assignable", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["taxonomy_version"],
            ["taxonomy_version.version"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_version", "parent_code"],
            ["taxonomy_node.taxonomy_version", "taxonomy_node.code"],
            name="fk_taxonomy_node_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("taxonomy_version", "code"),
        sa.UniqueConstraint("taxonomy_version", "name", name="uq_taxonomy_node_name"),
    )
    op.create_index(
        "ix_taxonomy_node_parent",
        "taxonomy_node",
        ["taxonomy_version", "parent_code"],
        unique=False,
    )

    op.create_table(
        "normalization_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("seed_list_version", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("tag_map_version", sa.String(length=50), nullable=False),
        sa.Column("overrides_version", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'running'"),
            nullable=False,
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
        sa.Column("report_path", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_review', 'failed')",
            name="ck_normalization_run_status",
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_normalization_run_finished_at",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_version"],
            ["taxonomy_version.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_normalization_run_status", "normalization_run", ["status"], unique=False)
    op.create_index(
        "ix_normalization_run_started_at",
        "normalization_run",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        "ix_normalization_run_dataset_version",
        "normalization_run",
        ["dataset_version"],
        unique=False,
    )

    op.create_table(
        "normalization_issue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issue_key", sa.String(length=64), nullable=False),
        sa.Column("normalization_run_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_mbid", sa.String(length=36), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=True),
        sa.Column("issue_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'medium', 'high', 'blocking')",
            name="ck_normalization_issue_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'review', 'accepted', 'rejected', 'quarantined')",
            name="ck_normalization_issue_status",
        ),
        sa.ForeignKeyConstraint(
            ["normalization_run_id"],
            ["normalization_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_version"],
            ["taxonomy_version.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_key", name="uq_normalization_issue_key"),
    )
    op.create_index(
        "ix_normalization_issue_status",
        "normalization_issue",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_normalization_issue_entity",
        "normalization_issue",
        ["entity_type", "entity_mbid"],
        unique=False,
    )
    op.create_index(
        "ix_normalization_issue_run",
        "normalization_issue",
        ["normalization_run_id"],
        unique=False,
    )

    op.create_table(
        "normalization_issue_action",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("source_file", sa.Text(), nullable=True),
        sa.Column("previous_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('apply', 'review', 'accept', 'reject', 'quarantine', 'close')",
            name="ck_normalization_issue_action_action",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["normalization_issue.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_normalization_issue_action_issue",
        "normalization_issue_action",
        ["issue_id"],
        unique=False,
    )

    op.create_table(
        "release_group_subgenre",
        sa.Column("release_group_id", sa.Uuid(), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("subgenre_code", sa.String(length=50), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mapping_rule", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('accepted', 'review', 'quarantined')",
            name="ck_release_group_subgenre_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_release_group_subgenre_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["release_group_id"],
            ["release_group.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_record.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_version", "subgenre_code"],
            ["taxonomy_node.taxonomy_version", "taxonomy_node.code"],
            name="fk_release_group_subgenre_taxonomy",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("release_group_id", "taxonomy_version", "subgenre_code"),
    )
    op.create_index(
        "uq_release_group_subgenre_primary",
        "release_group_subgenre",
        ["release_group_id", "taxonomy_version"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.create_index(
        "ix_release_group_subgenre_taxonomy",
        "release_group_subgenre",
        ["taxonomy_version", "subgenre_code"],
        unique=False,
    )

    op.create_table(
        "artist_subgenre_classification",
        sa.Column("artist_id", sa.Uuid(), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("subgenre_code", sa.String(length=50), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mapping_rule", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('accepted', 'review', 'quarantined')",
            name="ck_artist_subgenre_classification_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_artist_subgenre_classification_confidence",
        ),
        sa.ForeignKeyConstraint(["artist_id"], ["artist.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_record.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_version", "subgenre_code"],
            ["taxonomy_node.taxonomy_version", "taxonomy_node.code"],
            name="fk_artist_subgenre_classification_taxonomy",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("artist_id", "taxonomy_version", "subgenre_code"),
    )
    op.create_index(
        "uq_artist_subgenre_classification_primary",
        "artist_subgenre_classification",
        ["artist_id", "taxonomy_version"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )

    op.create_table(
        "dataset_membership",
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("artist_id", sa.Uuid(), nullable=False),
        sa.Column("seed_list_version", sa.String(length=50), nullable=False),
        sa.Column("batch_id", sa.String(length=100), nullable=False),
        sa.Column(
            "lifecycle",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("added_in_version", sa.String(length=50), nullable=False),
        sa.Column("retired_in_version", sa.String(length=50), nullable=True),
        sa.Column("replaced_by_artist_id", sa.Uuid(), nullable=True),
        sa.Column("source_record_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'retired')",
            name="ck_dataset_membership_lifecycle",
        ),
        sa.CheckConstraint(
            "(lifecycle = 'active' AND retired_in_version IS NULL) OR "
            "(lifecycle = 'retired' AND retired_in_version IS NOT NULL)",
            name="ck_dataset_membership_retired",
        ),
        sa.ForeignKeyConstraint(["artist_id"], ["artist.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["replaced_by_artist_id"],
            ["artist.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["source_record.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("dataset_version", "artist_id"),
    )
    op.create_index(
        "ix_dataset_membership_artist",
        "dataset_membership",
        ["artist_id"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_membership_lifecycle",
        "dataset_membership",
        ["lifecycle"],
        unique=False,
    )

    op.add_column("source_record", sa.Column("raw_response_id", sa.Uuid(), nullable=True))
    op.add_column("source_record", sa.Column("http_status", sa.Integer(), nullable=True))
    op.add_column("source_record", sa.Column("api_version", sa.String(length=50), nullable=True))
    op.add_column(
        "source_record",
        sa.Column("dataset_version", sa.String(length=100), nullable=True),
    )
    op.add_column("source_record", sa.Column("ingest_run_id", sa.Uuid(), nullable=True))
    op.alter_column(
        "source_record",
        "fixture_version",
        existing_type=sa.String(length=50),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_source_record_http_status",
        "source_record",
        "http_status IS NULL OR http_status BETWEEN 100 AND 599",
    )
    op.create_unique_constraint(
        "uq_source_record_raw_response",
        "source_record",
        ["raw_response_id"],
    )
    op.create_foreign_key(
        "source_record_raw_response_id_fkey",
        "source_record",
        "raw_response",
        ["raw_response_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "source_record_ingest_run_id_fkey",
        "source_record",
        "ingest_run",
        ["ingest_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_source_record_dataset_version",
        "source_record",
        ["dataset_version"],
        unique=False,
    )

    op.add_column(
        "recording_release",
        sa.Column("track_number", sa.String(length=20), nullable=True),
    )

    op.add_column(
        "artist_subgenre",
        sa.Column("taxonomy_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "artist_subgenre",
        sa.Column("status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "artist_subgenre",
        sa.Column("mapping_rule", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "artist_subgenre",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_artist_subgenre_status",
        "artist_subgenre",
        "status IS NULL OR status IN ('accepted', 'review', 'quarantined')",
    )
    op.create_foreign_key(
        "artist_subgenre_taxonomy_version_fkey",
        "artist_subgenre",
        "taxonomy_version",
        ["taxonomy_version"],
        ["version"],
        ondelete="RESTRICT",
    )

    op.execute(
        sa.text(
            "INSERT INTO role (code, name, category) "
            "VALUES ('assistant-producer', 'Assistant producer', 'extended') "
            "ON CONFLICT (code) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "artist_subgenre_taxonomy_version_fkey",
        "artist_subgenre",
        type_="foreignkey",
    )
    op.drop_constraint("ck_artist_subgenre_status", "artist_subgenre", type_="check")
    op.drop_column("artist_subgenre", "updated_at")
    op.drop_column("artist_subgenre", "mapping_rule")
    op.drop_column("artist_subgenre", "status")
    op.drop_column("artist_subgenre", "taxonomy_version")
    op.drop_column("recording_release", "track_number")

    op.drop_index("ix_source_record_dataset_version", table_name="source_record")
    op.drop_constraint("source_record_ingest_run_id_fkey", "source_record", type_="foreignkey")
    op.drop_constraint(
        "source_record_raw_response_id_fkey",
        "source_record",
        type_="foreignkey",
    )
    op.drop_constraint("uq_source_record_raw_response", "source_record", type_="unique")
    op.drop_constraint("ck_source_record_http_status", "source_record", type_="check")
    op.drop_column("source_record", "ingest_run_id")
    op.drop_column("source_record", "dataset_version")
    op.drop_column("source_record", "api_version")
    op.drop_column("source_record", "http_status")
    op.drop_column("source_record", "raw_response_id")

    op.drop_table("dataset_membership")
    op.drop_table("artist_subgenre_classification")
    op.drop_table("release_group_subgenre")
    op.drop_table("normalization_issue_action")
    op.drop_table("normalization_issue")
    op.drop_table("normalization_run")
    op.drop_table("taxonomy_node")
    op.drop_table("taxonomy_version")
