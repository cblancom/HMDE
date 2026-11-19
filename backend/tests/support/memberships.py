from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import Artist, DatasetMembership


def seed_dataset_memberships(
    session: Session,
    dataset_version: str,
    *,
    seed_list_version: str = "0.2.0",
    batch_id: str = "v0.1.0",
    added_in_version: str = "0.1.0",
) -> None:
    for artist in session.scalars(select(Artist)).all():
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
