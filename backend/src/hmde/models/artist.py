"""Artist and external identifier models."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hmde.db.base import Base


class Artist(Base):
    __tablename__ = "artist"
    __table_args__ = (
        CheckConstraint(
            "type IN ('person', 'group', 'other')",
            name="ck_artist_type",
        ),
        Index("ix_artist_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    mbid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    disambiguation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )


class ExternalId(Base):
    __tablename__ = "external_id"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "source",
            "external_id",
            name="uq_external_id_entity_source",
        ),
        Index("ix_external_id_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
