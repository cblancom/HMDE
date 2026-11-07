"""Ingestion run, raw response and error models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class IngestRun(Base):
    __tablename__ = "ingest_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_errors', 'failed')",
            name="ck_ingest_run_status",
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) OR "
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name="ck_ingest_run_finished_at",
        ),
        Index("ix_ingest_run_status", "status"),
        Index("ix_ingest_run_started_at", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    seed_list_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snapshot_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RawResponse(Base):
    __tablename__ = "raw_response"
    __table_args__ = (
        UniqueConstraint("request_key", "payload_hash", name="uq_raw_response_request_payload"),
        CheckConstraint(
            "http_status BETWEEN 100 AND 599",
            name="ck_raw_response_http_status",
        ),
        Index("ix_raw_response_request_key", "request_key"),
        Index("ix_raw_response_source_external_id", "source", "external_id"),
        Index("ix_raw_response_first_ingest_run_id", "first_ingest_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    first_ingest_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ingest_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    request_params: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_path: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    api_version: Mapped[str] = mapped_column(String(50), nullable=False)


class IngestError(Base):
    __tablename__ = "ingest_error"
    __table_args__ = (
        CheckConstraint("attempts >= 1", name="ck_ingest_error_attempts"),
        Index("ix_ingest_error_ingest_run_id", "ingest_run_id"),
        Index("ix_ingest_error_band_mbid", "band_mbid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    ingest_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ingest_run.id", ondelete="CASCADE"),
        nullable=False,
    )
    band_mbid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    request_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
