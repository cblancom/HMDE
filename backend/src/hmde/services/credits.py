"""Credit read services."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hmde.models import Artist, Credit, ReleaseGroup, Role
from hmde.schemas.api import CreditListItem


def list_credits(
    session: Session,
    *,
    album_id: UUID | None,
    band_id: UUID | None,
    artist_id: UUID | None,
    role: str | None,
    scope: str | None,
    limit: int,
    offset: int,
) -> tuple[list[CreditListItem], int]:
    conditions = []
    if album_id:
        conditions.append(Credit.release_group_id == album_id)
    if band_id:
        conditions.append(ReleaseGroup.artist_id == band_id)
    if artist_id:
        conditions.append(Credit.artist_id == artist_id)
    if role:
        conditions.append(Credit.role_code == role)
    if scope:
        conditions.append(Credit.scope == scope)
    band = Artist.__table__.alias("band")
    statement = (
        select(
            Credit,
            ReleaseGroup.title.label("album_title"),
            Artist.name.label("artist_name"),
            Role.name.label("role_name"),
            band.c.id.label("band_id"),
            band.c.name.label("band_name"),
        )
        .join(ReleaseGroup, ReleaseGroup.id == Credit.release_group_id)
        .join(band, band.c.id == ReleaseGroup.artist_id)
        .join(Artist, Artist.id == Credit.artist_id)
        .join(Role, Role.code == Credit.role_code)
        .where(*conditions)
        .order_by(ReleaseGroup.title, Artist.name, Role.name, Credit.id)
        .limit(limit)
        .offset(offset)
    )
    total_statement = (
        select(func.count(Credit.id))
        .join(ReleaseGroup, ReleaseGroup.id == Credit.release_group_id)
        .where(*conditions)
    )
    items = [
        CreditListItem(
            id=credit.id,
            album_id=credit.release_group_id,
            album_title=str(album_title),
            band_id=band_id_value,
            band_name=str(band_name),
            artist_id=credit.artist_id,
            artist_name=str(artist_name),
            role=credit.role_code,
            role_name=str(role_name),
            scope=credit.scope,
            confidence=credit.confidence,
            status=credit.status,
        )
        for (
            credit,
            album_title,
            artist_name,
            role_name,
            band_id_value,
            band_name,
        ) in session.execute(statement).all()
    ]
    return items, int(session.scalar(total_statement) or 0)
