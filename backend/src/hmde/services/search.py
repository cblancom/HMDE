"""Bounded grouped search."""

from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from hmde.models import Artist, ArtistSubgenre, Credit, ReleaseGroup, Subgenre
from hmde.schemas.api import (
    SearchAlbumItem,
    SearchBandItem,
    SearchProducerItem,
    SearchResponse,
)


def search(session: Session, q: str, limit: int) -> SearchResponse:
    query = q.strip()
    if not query:
        return SearchResponse(query=query, bands=[], albums=[], producers=[])
    pattern = f"%{query}%"
    bands = session.execute(
        select(Artist.id, Artist.name, Subgenre.name)
        .join(ArtistSubgenre, ArtistSubgenre.artist_id == Artist.id)
        .join(Subgenre, Subgenre.code == ArtistSubgenre.subgenre_code)
        .where(ArtistSubgenre.is_primary.is_(True), Artist.name.ilike(pattern))
        .order_by(Artist.name, Artist.id)
        .limit(limit)
    ).all()
    albums = session.execute(
        select(ReleaseGroup.id, ReleaseGroup.title, Artist.name, ReleaseGroup.first_release_date)
        .join(Artist, Artist.id == ReleaseGroup.artist_id)
        .where(ReleaseGroup.title.ilike(pattern))
        .order_by(ReleaseGroup.title, ReleaseGroup.id)
        .limit(limit)
    ).all()
    producers = session.execute(
        select(Artist.id, Artist.name)
        .where(
            Artist.name.ilike(pattern),
            exists(
                select(Credit.id).where(
                    Credit.artist_id == Artist.id,
                    Credit.role_code.in_(("producer", "co-producer")),
                )
            ),
        )
        .order_by(Artist.name, Artist.id)
        .limit(limit)
    ).all()
    return SearchResponse(
        query=query,
        bands=[SearchBandItem(id=row.id, name=row.name, subgenre=row[2]) for row in bands],
        albums=[
            SearchAlbumItem(
                id=row.id,
                title=row.title,
                band_name=row[2],
                year=row.first_release_date.year if row.first_release_date else None,
            )
            for row in albums
        ],
        producers=[SearchProducerItem(id=row.id, name=row.name) for row in producers],
    )
