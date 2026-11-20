from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import Artist, ArtistSubgenre, DatasetMembership


def seed_dataset_memberships(
    session: Session,
    dataset_version: str,
    *,
    seed_list_version: str = "0.2.0",
    batch_id: str = "v0.1.0",
    added_in_version: str = "0.1.0",
    bands_only: bool = False,
) -> None:
    query = select(Artist)
    if bands_only:
        query = query.join(ArtistSubgenre, ArtistSubgenre.artist_id == Artist.id).distinct()
    for artist in session.scalars(query).all():
        key = (dataset_version, artist.id)
        if session.get(DatasetMembership, key) is not None:
            continue
        session.add(
            DatasetMembership(
                dataset_version=dataset_version,
                artist_id=artist.id,
                seed_list_version=seed_list_version,
                batch_id=batch_id,
                lifecycle="active",
                added_in_version=added_in_version,
                source_record_id=artist.source_record_id,
            )
        )
    session.flush()
