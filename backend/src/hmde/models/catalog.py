"""Release group, release, recording and track models."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hmde.db.base import Base


class ReleaseGroup(Base):
    __tablename__ = "release_group"
    __table_args__ = (
        Index("ix_release_group_artist_id", "artist_id"),
        Index("ix_release_group_first_release_date", "first_release_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    mbid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    artist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("artist.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    first_release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_release_precision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    primary_type: Mapped[str] = mapped_column(String(20), nullable=False, default="album")
    secondary_types: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    disambiguation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )


class Release(Base):
    __tablename__ = "release"
    __table_args__ = (Index("ix_release_release_group_id", "release_group_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    mbid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    release_group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("release_group.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    release_date_precision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )


class Recording(Base):
    __tablename__ = "recording"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    mbid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )


class RecordingRelease(Base):
    __tablename__ = "recording_release"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "recording_id",
            name="uq_recording_release",
        ),
        Index("ix_recording_release_release_id", "release_id"),
        Index("ix_recording_release_recording_id", "recording_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    release_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("release.id", ondelete="CASCADE"),
        nullable=False,
    )
    recording_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("recording.id", ondelete="CASCADE"),
        nullable=False,
    )
    disc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    position: Mapped[str | None] = mapped_column(String(20), nullable=True)
