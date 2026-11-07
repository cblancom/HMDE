"""Band graph read service."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import Artist, ArtistSubgenre, Credit, FixtureLoad, ReleaseGroup
from hmde.schemas.graph import BandGraphResponse, GraphEdge, GraphMeta, GraphNode

CORE_PRODUCER_ROLES = ("producer", "co-producer")


def get_band_graph(session: Session, band_id: UUID) -> BandGraphResponse | None:
    band = session.execute(
        select(Artist)
        .join(ArtistSubgenre, ArtistSubgenre.artist_id == Artist.id)
        .where(
            Artist.id == band_id,
            ArtistSubgenre.is_primary.is_(True),
        )
    ).scalar_one_or_none()
    if band is None:
        return None

    rows = session.execute(
        select(
            Credit.artist_id,
            Artist.name,
            Credit.role_code,
            ReleaseGroup.title,
        )
        .join(Artist, Credit.artist_id == Artist.id)
        .join(ReleaseGroup, Credit.release_group_id == ReleaseGroup.id)
        .where(
            ReleaseGroup.artist_id == band_id,
            Credit.role_code.in_(CORE_PRODUCER_ROLES),
        )
        .order_by(Artist.name, ReleaseGroup.title)
    ).all()

    producer_names: dict[UUID, str] = {}
    producer_roles: dict[UUID, set[str]] = defaultdict(set)
    producer_albums: dict[UUID, set[str]] = defaultdict(set)
    for artist_id, artist_name, role_code, album_title in rows:
        producer_names[artist_id] = artist_name
        producer_roles[artist_id].add(role_code)
        producer_albums[artist_id].add(album_title)

    band_id_text = str(band.id)
    nodes = [GraphNode(id=band_id_text, label=band.name, type="band")]
    edges: list[GraphEdge] = []

    for artist_id, producer_name in sorted(
        producer_names.items(),
        key=lambda item: (item[1].casefold(), str(item[0])),
    ):
        producer_id_text = str(artist_id)
        role = "producer" if "producer" in producer_roles[artist_id] else "co-producer"
        album_titles = sorted(producer_albums[artist_id])
        nodes.append(
            GraphNode(
                id=producer_id_text,
                label=producer_name,
                type="producer",
            )
        )
        edges.append(
            GraphEdge(
                source=band_id_text,
                target=producer_id_text,
                type="produced",
                role=role,
                album_count=len(album_titles),
                albums=album_titles,
            )
        )

    fixture_version = session.scalar(
        select(FixtureLoad.version)
        .order_by(FixtureLoad.loaded_at.desc(), FixtureLoad.id.desc())
        .limit(1)
    )

    return BandGraphResponse(
        nodes=nodes,
        edges=edges,
        meta=GraphMeta(fixture_version=fixture_version or "unknown"),
    )
