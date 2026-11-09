"""quality layer

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quality_rule_catalogue",
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'approved'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('approved', 'retired')",
            name="ck_quality_rule_catalogue_status",
        ),
        sa.PrimaryKeyConstraint("version"),
    )

    op.create_table(
        "quality_rule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("catalogue_version", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("dimension", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("entity_scope", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected", sa.Text(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "dimension IN ('structural', 'completeness', 'validity', 'consistency', 'coverage')",
            name="ck_quality_rule_dimension",
        ),
        sa.CheckConstraint(
            "severity IN ('blocking', 'high', 'medium', 'info')",
            name="ck_quality_rule_severity",
        ),
        sa.ForeignKeyConstraint(
            ["catalogue_version"],
            ["quality_rule_catalogue.version"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "catalogue_version",
            "code",
            name="uq_quality_rule_catalogue_code",
        ),
    )
    op.create_index(
        "ix_quality_rule_catalogue",
        "quality_rule",
        ["catalogue_version"],
        unique=False,
    )

    op.create_table(
        "quality_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("normalization_run_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("catalogue_version", sa.String(length=50), nullable=False),
        sa.Column("code_version", sa.String(length=100), nullable=False),
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
            "status IN ('running', 'completed', 'completed_with_findings', 'blocked', 'failed')",
            name="ck_quality_run_status",
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_quality_run_finished_at",
        ),
        sa.ForeignKeyConstraint(
            ["normalization_run_id"],
            ["normalization_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["catalogue_version"],
            ["quality_rule_catalogue.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quality_run_status", "quality_run", ["status"], unique=False)
    op.create_index("ix_quality_run_started_at", "quality_run", ["started_at"], unique=False)
    op.create_index(
        "ix_quality_run_normalization_run",
        "quality_run",
        ["normalization_run_id"],
        unique=False,
    )

    op.create_table(
        "quality_finding",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quality_run_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("finding_key", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_mbid", sa.String(length=36), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column(
            "observed_value",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "expected_value",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "details",
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
            "severity IN ('blocking', 'high', 'medium', 'info')",
            name="ck_quality_finding_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'accepted', 'exceptional', 'quarantined', 'resolved')",
            name="ck_quality_finding_status",
        ),
        sa.ForeignKeyConstraint(
            ["quality_run_id"],
            ["quality_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["rule_id"], ["quality_rule.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "quality_run_id",
            "finding_key",
            name="uq_quality_finding_run_key",
        ),
    )
    op.create_index("ix_quality_finding_run", "quality_finding", ["quality_run_id"], unique=False)
    op.create_index("ix_quality_finding_rule", "quality_finding", ["rule_id"], unique=False)
    op.create_index("ix_quality_finding_status", "quality_finding", ["status"], unique=False)
    op.create_index(
        "ix_quality_finding_entity",
        "quality_finding",
        ["entity_type", "entity_mbid"],
        unique=False,
    )

    op.create_table(
        "quality_exception",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("catalogue_version", sa.String(length=50), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("exception_key", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_mbid", sa.String(length=36), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=False),
        sa.Column("approved_at", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'retired')",
            name="ck_quality_exception_status",
        ),
        sa.ForeignKeyConstraint(
            ["catalogue_version"],
            ["quality_rule_catalogue.version"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["rule_id"], ["quality_rule.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exception_key", name="uq_quality_exception_key"),
    )
    op.create_index(
        "ix_quality_exception_rule_entity",
        "quality_exception",
        ["rule_id", "entity_type", "entity_mbid"],
        unique=False,
    )

    op.create_table(
        "quality_metric",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quality_run_id", sa.Uuid(), nullable=False),
        sa.Column("metric_code", sa.String(length=50), nullable=False),
        sa.Column("dimension", sa.String(length=20), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_key", sa.String(length=200), nullable=False),
        sa.Column("numerator", sa.Float(), nullable=False),
        sa.Column("denominator", sa.Float(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=True),
        sa.Column(
            "details",
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
        sa.ForeignKeyConstraint(
            ["quality_run_id"],
            ["quality_run.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "quality_run_id",
            "metric_code",
            "scope_type",
            "scope_key",
            name="uq_quality_metric_run_scope",
        ),
    )
    op.create_index("ix_quality_metric_run", "quality_metric", ["quality_run_id"], unique=False)
    op.create_index("ix_quality_metric_code", "quality_metric", ["metric_code"], unique=False)


def downgrade() -> None:
    op.drop_table("quality_metric")
    op.drop_table("quality_exception")
    op.drop_table("quality_finding")
    op.drop_table("quality_run")
    op.drop_table("quality_rule")
    op.drop_table("quality_rule_catalogue")
