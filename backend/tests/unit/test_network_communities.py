from __future__ import annotations

import uuid
from datetime import date

from hmde.network.graph import build_producer_album_layer, build_producer_band_layer
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary
from hmde.network.metrics import compute_metrics


def _album() -> AlbumRow:
    return AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title="Album",
        first_release_date=date(1991, 1, 1),
        band_id=uuid.uuid4(),
        band_name="Band",
        band_mbid=str(uuid.uuid4()),
        band_type="group",
        band_country="US",
        primary_code="heavy-metal",
        primary_status="approved",
    )


def _row(producer_id: uuid.UUID, album: AlbumRow) -> ProducerAlbumRoleRow:
    return ProducerAlbumRoleRow(
        producer_id=producer_id,
        producer_name=str(producer_id),
        producer_mbid=str(uuid.uuid4()),
        producer_type="person",
        producer_country="GB",
        album_id=album.album_id,
        role_code="producer",
        supporting_recordings=1,
        album_recordings=1,
        support_ratio=1.0,
        has_release_group_scope=True,
        scope_mix={"release_group": 1},
        evidence={"credit_ids": [], "source_record_ids": []},
    )


def test_communities_are_deterministic_and_cover_producers() -> None:
    album_a = _album()
    album_b = _album()
    p1, p2, p3, p4 = (uuid.uuid4() for _ in range(4))
    data = NetworkData(
        albums={album_a.album_id: album_a, album_b.album_id: album_b},
        producer_albums=(
            _row(p1, album_a),
            _row(p2, album_a),
            _row(p3, album_b),
            _row(p4, album_b),
        ),
        quality=QualitySummary({}, 0, 0, 0, ()),
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    first = compute_metrics(data, album_layer, band_layer)
    second = compute_metrics(data, album_layer, band_layer)
    assert [community.community_key for community in first.communities] == [
        community.community_key for community in second.communities
    ]
    members = {member for community in first.communities for member in community.member_keys}
    assert members == {f"artist:{producer_id}" for producer_id in (p1, p2, p3, p4)}
    assert all(community.algorithm == "louvain" for community in first.communities)
