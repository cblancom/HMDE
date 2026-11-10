from __future__ import annotations

import uuid
from datetime import date

from hmde.network.graph import (
    PRODUCER_BAND,
    album_key,
    artist_key,
    build_producer_album_layer,
    build_producer_band_layer,
)
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary


def _album(
    *, band_id: uuid.UUID | None = None, band_type: str = "group", year: int = 1991
) -> AlbumRow:
    return AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title="Album",
        first_release_date=date(year, 1, 1),
        band_id=band_id or uuid.uuid4(),
        band_name="Band",
        band_mbid=str(uuid.uuid4()),
        band_type=band_type,
        band_country="US",
        primary_code="heavy-metal",
        primary_status="approved",
    )


def _row(
    producer_id: uuid.UUID, album: AlbumRow, *, role: str = "producer"
) -> ProducerAlbumRoleRow:
    return ProducerAlbumRoleRow(
        producer_id=producer_id,
        producer_name="Producer",
        producer_mbid=str(uuid.uuid4()),
        producer_type="person",
        producer_country="GB",
        album_id=album.album_id,
        role_code=role,
        supporting_recordings=1,
        album_recordings=1,
        support_ratio=1.0,
        has_release_group_scope=True,
        scope_mix={"release_group": 1},
        evidence={"credit_ids": [], "source_record_ids": []},
    )


def _data(albums: list[AlbumRow], rows: list[ProducerAlbumRoleRow]) -> NetworkData:
    return NetworkData(
        albums={album.album_id: album for album in albums},
        producer_albums=tuple(rows),
        quality=QualitySummary({}, 0, 0, 0, ()),
    )


def test_derives_one_edge_per_producer_band_with_album_evidence() -> None:
    band_id = uuid.uuid4()
    album_a = _album(band_id=band_id, year=1991)
    album_b = _album(band_id=band_id, year=1995)
    producer_id = uuid.uuid4()
    data = _data([album_a, album_b], [_row(producer_id, album_a), _row(producer_id, album_b)])
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    assert len(band_layer.edges) == 1
    edge = band_layer.edges[0]
    assert edge.layer_code == PRODUCER_BAND
    assert edge.weight == 2.0
    assert edge.evidence["album_count"] == 2
    assert edge.evidence["first_year"] == 1991
    assert edge.evidence["last_year"] == 1995
    assert set(edge.evidence["album_ids"]) == {str(album_a.album_id), str(album_b.album_id)}


def test_band_layer_has_no_album_nodes() -> None:
    album = _album()
    producer_id = uuid.uuid4()
    data = _data([album], [_row(producer_id, album)])
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    assert all(node.node_type != "album" for node in band_layer.nodes)
    assert album_key(album.album_id) not in {node.node_key for node in band_layer.nodes}


def test_producer_band_counts_reconcile_with_album_layer() -> None:
    band_a = uuid.uuid4()
    band_b = uuid.uuid4()
    album_a = _album(band_id=band_a)
    album_b = _album(band_id=band_a)
    album_c = _album(band_id=band_b)
    producer_id = uuid.uuid4()
    data = _data(
        [album_a, album_b, album_c],
        [_row(producer_id, album_a), _row(producer_id, album_b), _row(producer_id, album_c)],
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    assert sum(int(edge.evidence["album_count"]) for edge in band_layer.edges) == 3
    assert {node.node_key for node in band_layer.nodes if node.roles == ("band",)} == {
        artist_key(band_a),
        artist_key(band_b),
    }


def test_solo_artist_band_is_included() -> None:
    album = _album(band_type="person")
    producer_id = uuid.uuid4()
    data = _data([album], [_row(producer_id, album)])
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    assert len(band_layer.edges) == 1
    assert band_layer.edges[0].target_key == artist_key(album.band_id)
