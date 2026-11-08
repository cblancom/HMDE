"""Credits, roles and provenance models."""

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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hmde.db.base import Base


class SourceRecord(Base):
    __tablename__ = "source_record"
    __table_args__ = (
        CheckConstraint(
            "http_status IS NULL OR http_status BETWEEN 100 AND 599",
            name="ck_source_record_http_status",
        ),
        UniqueConstraint("raw_response_id", name="uq_source_record_raw_response"),
        Index("ix_source_record_source_external_id", "source", "external_id"),
        Index("ix_source_record_dataset_version", "dataset_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    fixture_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_response_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("raw_response.id", ondelete="RESTRICT"),
        nullable=True,
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ingest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ingest_run.id", ondelete="RESTRICT"),
        nullable=True,
    )


class Role(Base):
    __tablename__ = "role"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)


class Credit(Base):
    __tablename__ = "credit"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('release_group', 'release', 'recording')",
            name="ck_credit_scope",
        ),
        CheckConstraint(
            "status IN ('confirmed', 'inferred', 'conflicting', 'quarantined')",
            name="ck_credit_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_credit_confidence",
        ),
        CheckConstraint(
            "("
            "scope = 'release_group' AND release_id IS NULL AND recording_id IS NULL"
            ") OR ("
            "scope = 'release' AND release_id IS NOT NULL AND recording_id IS NULL"
            ") OR ("
            "scope = 'recording' AND recording_id IS NOT NULL"
            ")",
            name="ck_credit_scope_target",
        ),
        Index("ix_credit_release_group_id", "release_group_id"),
        Index("ix_credit_artist_id", "artist_id"),
        Index("ix_credit_recording_id", "recording_id"),
        Index("ix_credit_role_code", "role_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    artist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("artist.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("role.code", ondelete="RESTRICT"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    release_group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("release_group.id", ondelete="CASCADE"),
        nullable=False,
    )
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("release.id", ondelete="RESTRICT"),
        nullable=True,
    )
    recording_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("recording.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="confirmed",
    )
    credited_as: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
