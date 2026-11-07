"""Fixture load metadata."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from hmde.db.base import Base


class FixtureLoad(Base):
    __tablename__ = "fixture_load"
    __table_args__ = (Index("ix_fixture_load_version", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    band_count: Mapped[int] = mapped_column(Integer, nullable=False)
    album_count: Mapped[int] = mapped_column(Integer, nullable=False)
    credit_count: Mapped[int] = mapped_column(Integer, nullable=False)
