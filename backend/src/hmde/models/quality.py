"""Quality catalogue, run, finding, exception and metric models."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
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


class QualityRuleCatalogue(Base):
    __tablename__ = "quality_rule_catalogue"
    __table_args__ = (
        CheckConstraint(
            "status IN ('approved', 'retired')",
            name="ck_quality_rule_catalogue_status",
        ),
    )

    version: Mapped[str] = mapped_column(String(50), primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="approved",
        server_default=text("'approved'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QualityRule(Base):
    __tablename__ = "quality_rule"
    __table_args__ = (
        CheckConstraint(
            "dimension IN ('structural', 'completeness', 'validity', 'consistency', 'coverage')",
            name="ck_quality_rule_dimension",
        ),
        CheckConstraint(
            "severity IN ('blocking', 'high', 'medium', 'info')",
            name="ck_quality_rule_severity",
        ),
        UniqueConstraint("catalogue_version", "code", name="uq_quality_rule_catalogue_code"),
        Index("ix_quality_rule_catalogue", "catalogue_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    catalogue_version: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("quality_rule_catalogue.version", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dimension: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_scope: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected: Mapped[str] = mapped_column(Text, nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class QualityRun(Base):
    __tablename__ = "quality_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_findings', 'blocked', 'failed')",
            name="ck_quality_run_status",
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_quality_run_finished_at",
        ),
        Index("ix_quality_run_status", "status"),
        Index("ix_quality_run_started_at", "started_at"),
        Index("ix_quality_run_normalization_run", "normalization_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    normalization_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("normalization_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    catalogue_version: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("quality_rule_catalogue.version", ondelete="RESTRICT"),
        nullable=False,
    )
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


class QualityFinding(Base):
    __tablename__ = "quality_finding"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('blocking', 'high', 'medium', 'info')",
            name="ck_quality_finding_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'accepted', 'exceptional', 'quarantined', 'resolved')",
            name="ck_quality_finding_status",
        ),
        UniqueConstraint("quality_run_id", "finding_key", name="uq_quality_finding_run_key"),
        Index("ix_quality_finding_run", "quality_run_id"),
        Index("ix_quality_finding_rule", "rule_id"),
        Index("ix_quality_finding_status", "status"),
        Index("ix_quality_finding_entity", "entity_type", "entity_mbid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    quality_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("quality_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("quality_rule.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finding_key: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_mbid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default=text("'open'"),
    )
    observed_value: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    expected_value: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QualityException(Base):
    __tablename__ = "quality_exception"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'retired')",
            name="ck_quality_exception_status",
        ),
        UniqueConstraint("exception_key", name="uq_quality_exception_key"),
        Index("ix_quality_exception_rule_entity", "rule_id", "entity_type", "entity_mbid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    catalogue_version: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("quality_rule_catalogue.version", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("quality_rule.id", ondelete="RESTRICT"),
        nullable=False,
    )
    exception_key: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_mbid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QualityMetric(Base):
    __tablename__ = "quality_metric"
    __table_args__ = (
        UniqueConstraint(
            "quality_run_id",
            "metric_code",
            "scope_type",
            "scope_key",
            name="uq_quality_metric_run_scope",
        ),
        Index("ix_quality_metric_run", "quality_run_id"),
        Index("ix_quality_metric_code", "metric_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    quality_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("quality_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False)
    dimension: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(200), nullable=False)
    numerator: Mapped[float] = mapped_column(Float, nullable=False)
    denominator: Mapped[float] = mapped_column(Float, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    missing_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
