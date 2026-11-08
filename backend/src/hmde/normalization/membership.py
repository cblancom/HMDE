"""Dataset membership and lifecycle synchronization."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from hmde.models import Artist, DatasetMembership

from .errors import ProvenanceError
from .seed import SeedMembership


@dataclass(frozen=True, slots=True)
class MembershipCounts:
    bands: int
    active: int
    retired: int
    created: int
    updated: int


def sync_membership(
    session: Session,
    *,
    dataset_version: str,
    seed_list: SeedMembership,
    artist_ids: dict[str, uuid.UUID],
) -> MembershipCounts:
    created = updated = active = retired = 0
    for band in seed_list.bands:
        artist_id = artist_ids.get(band.mbid)
        if artist_id is None:
            raise ProvenanceError(f"seed band is not normalized: {band.mbid}")
        artist = session.get(Artist, artist_id)
        if artist is None:
            raise ProvenanceError(f"canonical artist disappeared: {band.mbid}")
        row = session.get(DatasetMembership, (dataset_version, artist_id))
        if row is None:
            row = DatasetMembership(
                dataset_version=dataset_version,
                artist_id=artist_id,
                seed_list_version=seed_list.version,
                batch_id=band.batch_id or "unknown",
                lifecycle=band.lifecycle,
                added_in_version=_added_version(seed_list.version, band.batch_id),
                retired_in_version=None,
                replaced_by_artist_id=None,
                source_record_id=artist.source_record_id,
            )
            session.add(row)
            created += 1
        else:
            row.seed_list_version = seed_list.version
            row.batch_id = band.batch_id or "unknown"
            row.lifecycle = band.lifecycle
            row.added_in_version = _added_version(seed_list.version, band.batch_id)
            row.source_record_id = artist.source_record_id
            updated += 1
        if band.lifecycle == "retired":
            retired += 1
        else:
            active += 1
    session.flush()
    return MembershipCounts(
        bands=len(seed_list.bands),
        active=active,
        retired=retired,
        created=created,
        updated=updated,
    )


def _added_version(seed_list_version: str, batch_id: str | None) -> str:
    if batch_id == "v0.1.0":
        return "0.1.0"
    return seed_list_version
