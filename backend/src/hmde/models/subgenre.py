"""Subgenre models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hmde.db.base import Base


class Subgenre(Base):
    __tablename__ = "subgenre"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class ArtistSubgenre(Base):
    __tablename__ = "artist_subgenre"
    __table_args__ = (Index("ix_artist_subgenre_subgenre_code", "subgenre_code"),)

    artist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("artist.id", ondelete="CASCADE"),
        primary_key=True,
    )
    subgenre_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("subgenre.code", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_record.id", ondelete="RESTRICT"),
        nullable=False,
    )
