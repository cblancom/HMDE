"""analytics layer

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_version", sa.String(length=64), nullable=False),
        sa.Column("normalization_run_id", sa.Uuid(), nullable=False),
        sa.Column("quality_run_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("graph_version", sa.String(length=50), nullable=False),
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
            "status IN ('running', 'completed', 'completed_with_limitations', 'failed')",
            name="ck_analysis_run_status",
        ),
        sa.CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_analysis_run_finished_at",
        ),
        sa.ForeignKeyConstraint(
            ["normalization_run_id"],
            ["normalization_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quality_run_id"],
            ["quality_run.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_run_version", "analysis_run", ["analysis_version"], unique=False)
    op.create_index("ix_analysis_run_status", "analysis_run", ["status"], unique=False)
    op.create_index(
        "ix_analysis_run_normalization_run",
        "analysis_run",
        ["normalization_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_run_quality_run",
        "analysis_run",
        ["quality_run_id"],
        unique=False,
    )

    op.create_table(
        "graph_node",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("node_key", sa.String(length=100), nullable=False),
        sa.Column("node_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("mbid", sa.String(length=36), nullable=True),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column(
            "roles",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint("node_type IN ('artist', 'album')", name="ck_graph_node_type"),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_run.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "node_key", name="uq_graph_node_run_key"),
    )
    op.create_index(
        "ix_graph_node_run_type",
        "graph_node",
        ["analysis_run_id", "node_type"],
        unique=False,
    )
    op.create_index(
        "ix_graph_node_run_label",
        "graph_node",
        ["analysis_run_id", "label"],
        unique=False,
    )

    op.create_table(
        "graph_edge",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("layer_code", sa.String(length=30), nullable=False),
        sa.Column("source_node_id", sa.Uuid(), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), nullable=False),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("supporting_recordings", sa.Integer(), nullable=True),
        sa.Column("album_recordings", sa.Integer(), nullable=True),
        sa.Column("support_ratio", sa.Float(), nullable=True),
        sa.Column(
            "scope_mix",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "layer_code IN ('producer_album', 'producer_band')",
            name="ck_graph_edge_layer",
        ),
        sa.CheckConstraint("weight >= 0", name="ck_graph_edge_weight"),
        sa.CheckConstraint(
            "support_ratio IS NULL OR (support_ratio >= 0 AND support_ratio <= 1)",
            name="ck_graph_edge_support_ratio",
        ),
        sa.CheckConstraint("source_node_id <> target_node_id", name="ck_graph_edge_no_self_loop"),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"],
            ["graph_node.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"],
            ["graph_node.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "layer_code",
            "source_node_id",
            "target_node_id",
            "role_code",
            name="uq_graph_edge_run_layer_nodes_role",
        ),
    )
    op.create_index(
        "ix_graph_edge_run_layer",
        "graph_edge",
        ["analysis_run_id", "layer_code"],
        unique=False,
    )
    op.create_index("ix_graph_edge_source", "graph_edge", ["source_node_id"], unique=False)
    op.create_index("ix_graph_edge_target", "graph_edge", ["target_node_id"], unique=False)

    op.create_table(
        "node_metric",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("layer_code", sa.String(length=30), nullable=False),
        sa.Column("metric_code", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("numerator", sa.Float(), nullable=True),
        sa.Column("denominator", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["node_id"], ["graph_node.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "node_id",
            "layer_code",
            "metric_code",
            name="uq_node_metric_run_node_layer_code",
        ),
    )
    op.create_index("ix_node_metric_run", "node_metric", ["analysis_run_id"], unique=False)
    op.create_index("ix_node_metric_code", "node_metric", ["metric_code"], unique=False)

    op.create_table(
        "producer_metric",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("producer_node_id", sa.Uuid(), nullable=False),
        sa.Column("metric_code", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("numerator", sa.Float(), nullable=True),
        sa.Column("denominator", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["producer_node_id"],
            ["graph_node.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "producer_node_id",
            "metric_code",
            name="uq_producer_metric_run_node_code",
        ),
    )
    op.create_index("ix_producer_metric_run", "producer_metric", ["analysis_run_id"], unique=False)
    op.create_index("ix_producer_metric_code", "producer_metric", ["metric_code"], unique=False)

    op.create_table(
        "temporal_metric",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("layer_code", sa.String(length=30), nullable=False),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_key", sa.String(length=50), nullable=False),
        sa.Column("metric_code", sa.String(length=50), nullable=False),
        sa.Column("numerator", sa.Float(), nullable=True),
        sa.Column("denominator", sa.Float(), nullable=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_run.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "layer_code",
            "scope_type",
            "scope_key",
            "metric_code",
            name="uq_temporal_metric_run_layer_scope_code",
        ),
    )
    op.create_index(
        "ix_temporal_metric_run_layer",
        "temporal_metric",
        ["analysis_run_id", "layer_code"],
        unique=False,
    )
    op.create_index(
        "ix_temporal_metric_code",
        "temporal_metric",
        ["metric_code"],
        unique=False,
    )

    op.create_table(
        "community",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("community_key", sa.String(length=64), nullable=False),
        sa.Column("algorithm", sa.String(length=50), nullable=False),
        sa.Column("resolution", sa.Float(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_run.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "community_key", name="uq_community_run_key"),
    )
    op.create_index("ix_community_run", "community", ["analysis_run_id"], unique=False)

    op.create_table(
        "community_membership",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("community_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_run.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["community_id"], ["community.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["node_id"], ["graph_node.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "community_id",
            "node_id",
            name="uq_community_membership_run_community_node",
        ),
    )
    op.create_index(
        "ix_community_membership_run",
        "community_membership",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_community_membership_community",
        "community_membership",
        ["community_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_community_membership_community", table_name="community_membership")
    op.drop_index("ix_community_membership_run", table_name="community_membership")
    op.drop_table("community_membership")
    op.drop_index("ix_community_run", table_name="community")
    op.drop_table("community")
    op.drop_index("ix_temporal_metric_code", table_name="temporal_metric")
    op.drop_index("ix_temporal_metric_run_layer", table_name="temporal_metric")
    op.drop_table("temporal_metric")
    op.drop_index("ix_producer_metric_code", table_name="producer_metric")
    op.drop_index("ix_producer_metric_run", table_name="producer_metric")
    op.drop_table("producer_metric")
    op.drop_index("ix_node_metric_code", table_name="node_metric")
    op.drop_index("ix_node_metric_run", table_name="node_metric")
    op.drop_table("node_metric")
    op.drop_index("ix_graph_edge_target", table_name="graph_edge")
    op.drop_index("ix_graph_edge_source", table_name="graph_edge")
    op.drop_index("ix_graph_edge_run_layer", table_name="graph_edge")
    op.drop_table("graph_edge")
    op.drop_index("ix_graph_node_run_label", table_name="graph_node")
    op.drop_index("ix_graph_node_run_type", table_name="graph_node")
    op.drop_table("graph_node")
    op.drop_index("ix_analysis_run_quality_run", table_name="analysis_run")
    op.drop_index("ix_analysis_run_normalization_run", table_name="analysis_run")
    op.drop_index("ix_analysis_run_status", table_name="analysis_run")
    op.drop_index("ix_analysis_run_version", table_name="analysis_run")
    op.drop_table("analysis_run")
