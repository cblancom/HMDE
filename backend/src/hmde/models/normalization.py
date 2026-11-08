"""Normalization, taxonomy, classification and membership models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
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


class TaxonomyVersion(Base):
    __tablename__ = "taxonomy_version"
    __table_args__ = (
        CheckConstraint(
            "status IN ('approved', 'retired')",
            name="ck_taxonomy_version_status",
        ),
        Index(
            "uq_taxonomy_version_current",
            "is_current",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    version: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="approved",
        server_default=text("'approved'"),
    )
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TaxonomyNode(Base):
    __tablename__ = "taxonomy_node"
    __table_args__ = (
        ForeignKeyConstraint(
            ["taxonomy_version", "parent_code"],
            ["taxonomy_node.taxonomy_version", "taxonomy_node.code"],
            name="fk_taxonomy_node_parent",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("taxonomy_version", "name", name="uq_taxonomy_node_name"),
        Index("ix_taxonomy_node_parent", "taxonomy_version", "parent_code"),
    )

    taxonomy_version: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("taxonomy_version.version", ondelete="CASCADE"),
        primary_key=True,
    )
    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assignable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class NormalizationRun(Base):
    __tablename__ = "normalization_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_review', 'failed')",
            name="ck_normalization_run_status",
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_normalization_run_finished_at",
        ),
        Index("ix_normalization_run_status", "status"),
        Index("ix_normalization_run_started_at", "started_at"),
        Index("ix_normalization_run_dataset_version", "dataset_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    seed_list_version: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("taxonomy_version.version", ondelete="RESTRICT"),
        nullable=False,
    )
    tag_map_version: Mapped[str] = mapped_column(String(50), nullable=False)
    overrides_version: Mapped[str] = mapped_column(String(50), nullable=False)
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
    code_version: Mapped[str] = mapped_column(String(100), nullable=False)
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


class NormalizationIssue(Base):
    __tablename__ = "normalization_issue"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'medium', 'high', 'blocking')",
            name="ck_normalization_issue_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'review', 'accepted', 'rejected', 'quarantined')",
            name="ck_normalization_issue_status",
        ),
        UniqueConstraint("issue_key", name="uq_normalization_issue_key"),
        Index("ix_normalization_issue_status", "status"),
        Index("ix_normalization_issue_entity", "entity_type", "entity_mbid"),
        Index("ix_normalization_issue_run", "normalization_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    issue_key: Mapped[str] = mapped_column(String(64), nullable=False)
    normalization_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("normalization_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_mbid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    taxonomy_version: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("taxonomy_version.version", ondelete="RESTRICT"),
        nullable=True,
    )
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default=text("'open'"),
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(
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


class NormalizationIssueAction(Base):
    __tablename__ = "normalization_issue_action"
    __table_args__ = (
        CheckConstraint(
            "action IN ('apply', 'review', 'accept', 'reject', 'quarantine', 'close')",
            name="ck_normalization_issue_action_action",
        ),
        Index("ix_normalization_issue_action_issue", "issue_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("normalization_issue.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_value: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ReleaseGroupSubgenre(Base):
    __tablename__ = "release_group_subgenre"
    __table_args__ = (
        ForeignKeyConstraint(
            ["taxonomy_version", "subgenre_code"],
            ["taxonomy_node.taxonomy_version", "taxonomy_node.code"],
            name="fk_release_group_subgenre_taxonomy",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('accepted', 'review', 'quarantined')",
            name="ck_release_group_subgenre_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_release_group_subgenre_confidence",
        ),
        Index(
            "uq_release_group_subgenre_primary",
            "release_group_id",
            "taxonomy_version",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
        Index("ix_release_group_subgenre_taxonomy", "taxonomy_version", "subgenre_code"),
    )

    release_group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("release_group.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    taxonomy_version: Mapped[str] = mapped_column(String(50), primary_key=True)
    subgenre_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    mapping_rule: Mapped[str] = mapped_column(String(100), nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence: Mapped[dict[str, object]] = mapped_column(
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


class ArtistSubgenreClassification(Base):
    __tablename__ = "artist_subgenre_classification"
    __table_args__ = (
        ForeignKeyConstraint(
            ["taxonomy_version", "subgenre_code"],
            ["taxonomy_node.taxonomy_version", "taxonomy_node.code"],
            name="fk_artist_subgenre_classification_taxonomy",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('accepted', 'review', 'quarantined')",
            name="ck_artist_subgenre_classification_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_artist_subgenre_classification_confidence",
        ),
        Index(
            "uq_artist_subgenre_classification_primary",
            "artist_id",
            "taxonomy_version",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    artist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("artist.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    taxonomy_version: Mapped[str] = mapped_column(String(50), primary_key=True)
    subgenre_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    mapping_rule: Mapped[str] = mapped_column(String(100), nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence: Mapped[dict[str, object]] = mapped_column(
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


class DatasetMembership(Base):
    __tablename__ = "dataset_membership"
    __table_args__ = (
        CheckConstraint(
            "lifecycle IN ('active', 'retired')",
            name="ck_dataset_membership_lifecycle",
        ),
        CheckConstraint(
            "(lifecycle = 'active' AND retired_in_version IS NULL) OR "
            "(lifecycle = 'retired' AND retired_in_version IS NOT NULL)",
            name="ck_dataset_membership_retired",
        ),
        Index("ix_dataset_membership_artist", "artist_id"),
        Index("ix_dataset_membership_lifecycle", "lifecycle"),
    )

    dataset_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    artist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("artist.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    seed_list_version: Mapped[str] = mapped_column(String(50), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(100), nullable=False)
    lifecycle: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    added_in_version: Mapped[str] = mapped_column(String(50), nullable=False)
    retired_in_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    replaced_by_artist_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("artist.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
