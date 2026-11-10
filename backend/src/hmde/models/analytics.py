"""Analytical graph run, node, edge, metric and community models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hmde.db.base import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_limitations', 'failed')",
            name="ck_analysis_run_status",
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_analysis_run_finished_at",
        ),
        Index("ix_analysis_run_version", "analysis_version"),
        Index("ix_analysis_run_status", "status"),
        Index("ix_analysis_run_normalization_run", "normalization_run_id"),
        Index("ix_analysis_run_quality_run", "quality_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_version: Mapped[str] = mapped_column(String(64), nullable=False)
    normalization_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("normalization_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quality_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("quality_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    graph_version: Mapped[str] = mapped_column(String(50), nullable=False)
    code_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="running",
        server_default=text("'running'"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parameters: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    counters: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    report_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class GraphNode(Base):
    __tablename__ = "graph_node"
    __table_args__ = (
        CheckConstraint("node_type IN ('artist', 'album')", name="ck_graph_node_type"),
        UniqueConstraint("analysis_run_id", "node_key", name="uq_graph_node_run_key"),
        Index("ix_graph_node_run_type", "analysis_run_id", "node_type"),
        Index("ix_graph_node_run_label", "analysis_run_id", "label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    node_key: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    mbid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    roles: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    attributes: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class GraphEdge(Base):
    __tablename__ = "graph_edge"
    __table_args__ = (
        CheckConstraint(
            "layer_code IN ('producer_album', 'producer_band')",
            name="ck_graph_edge_layer",
        ),
        CheckConstraint("weight >= 0", name="ck_graph_edge_weight"),
        CheckConstraint(
            "support_ratio IS NULL OR (support_ratio >= 0 AND support_ratio <= 1)",
            name="ck_graph_edge_support_ratio",
        ),
        CheckConstraint("source_node_id <> target_node_id", name="ck_graph_edge_no_self_loop"),
        UniqueConstraint(
            "analysis_run_id",
            "layer_code",
            "source_node_id",
            "target_node_id",
            "role_code",
            name="uq_graph_edge_run_layer_nodes_role",
        ),
        Index("ix_graph_edge_run_layer", "analysis_run_id", "layer_code"),
        Index("ix_graph_edge_source", "source_node_id"),
        Index("ix_graph_edge_target", "target_node_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    layer_code: Mapped[str] = mapped_column(String(30), nullable=False)
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("graph_node.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("graph_node.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role_code: Mapped[str] = mapped_column(String(50), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    supporting_recordings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    album_recordings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    support_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    scope_mix: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    evidence: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class NodeMetric(Base):
    __tablename__ = "node_metric"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "node_id",
            "layer_code",
            "metric_code",
            name="uq_node_metric_run_node_layer_code",
        ),
        Index("ix_node_metric_run", "analysis_run_id"),
        Index("ix_node_metric_code", "metric_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("graph_node.id", ondelete="RESTRICT"),
        nullable=False,
    )
    layer_code: Mapped[str] = mapped_column(String(30), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    numerator: Mapped[float | None] = mapped_column(Float, nullable=True)
    denominator: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class ProducerMetric(Base):
    __tablename__ = "producer_metric"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "producer_node_id",
            "metric_code",
            name="uq_producer_metric_run_node_code",
        ),
        Index("ix_producer_metric_run", "analysis_run_id"),
        Index("ix_producer_metric_code", "metric_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    producer_node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("graph_node.id", ondelete="RESTRICT"),
        nullable=False,
    )
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    numerator: Mapped[float | None] = mapped_column(Float, nullable=True)
    denominator: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class TemporalMetric(Base):
    __tablename__ = "temporal_metric"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "layer_code",
            "scope_type",
            "scope_key",
            "metric_code",
            name="uq_temporal_metric_run_layer_scope_code",
        ),
        Index("ix_temporal_metric_run_layer", "analysis_run_id", "layer_code"),
        Index("ix_temporal_metric_code", "metric_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    layer_code: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False)
    numerator: Mapped[float | None] = mapped_column(Float, nullable=True)
    denominator: Mapped[float | None] = mapped_column(Float, nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class Community(Base):
    __tablename__ = "community"
    __table_args__ = (
        UniqueConstraint("analysis_run_id", "community_key", name="uq_community_run_key"),
        Index("ix_community_run", "analysis_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    community_key: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    resolution: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )


class CommunityMembership(Base):
    __tablename__ = "community_membership"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "community_id",
            "node_id",
            name="uq_community_membership_run_community_node",
        ),
        Index("ix_community_membership_run", "analysis_run_id"),
        Index("ix_community_membership_community", "community_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("community.id", ondelete="RESTRICT"),
        nullable=False,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("graph_node.id", ondelete="RESTRICT"),
        nullable=False,
    )
