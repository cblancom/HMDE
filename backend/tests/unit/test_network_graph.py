from __future__ import annotations

import uuid
from datetime import date

from hmde.network.graph import (
    PRODUCER_ALBUM,
    album_key,
    artist_key,
    build_producer_album_layer,
)
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary


def _album(*, band_type: str = "group", year: int = 1991) -> AlbumRow:
    return AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title="Album",
        first_release_date=date(year, 1, 1),
        band_id=uuid.uuid4(),
        band_name="Band",
        band_mbid=str(uuid.uuid4()),
        band_type=band_type,
        band_country="US",
        primary_code="heavy-metal",
        primary_status="approved",
    )


def _row(
    producer_id: uuid.UUID,
    album: AlbumRow,
    *,
    producer_name: str = "Producer",
    role: str = "producer",
    ratio: float | None = 1.0,
    scope: str = "release_group",
) -> ProducerAlbumRoleRow:
    return ProducerAlbumRoleRow(
        producer_id=producer_id,
        producer_name=producer_name,
        producer_mbid=str(uuid.uuid4()),
        producer_type="person",
        producer_country="GB",
        album_id=album.album_id,
        role_code=role,
        supporting_recordings=1,
        album_recordings=1,
        support_ratio=ratio,
        has_release_group_scope=scope == "release_group",
        scope_mix={scope: 1},
        evidence={"credit_ids": [], "source_record_ids": []},
    )


def _data(albums: list[AlbumRow], rows: list[ProducerAlbumRoleRow]) -> NetworkData:
    return NetworkData(
        albums={album.album_id: album for album in albums},
        producer_albums=tuple(rows),
        quality=QualitySummary(
            findings={},
            active_exceptions=0,
            missing_dates=0,
            unclassified_albums=0,
            duplicate_labels=(),
        ),
    )


def test_builds_producer_and_album_nodes_without_band_nodes() -> None:
    album = _album()
    producer_id = uuid.uuid4()
    layer = build_producer_album_layer(_data([album], [_row(producer_id, album)]))
    assert {node.node_key for node in layer.nodes} == {
        artist_key(producer_id),
        album_key(album.album_id),
    }
    assert {node.node_type for node in layer.nodes} == {"artist", "album"}
    assert all(node.node_type != "band" for node in layer.nodes)
    assert layer.edges[0].layer_code == PRODUCER_ALBUM


def test_same_producer_id_uses_one_node() -> None:
    album_a = _album()
    album_b = _album(year=1995)
    producer_id = uuid.uuid4()
    layer = build_producer_album_layer(
        _data(
            [album_a, album_b],
            [
                _row(producer_id, album_a, producer_name="Martin Birch"),
                _row(producer_id, album_b, producer_name="Maartin Birch"),
            ],
        )
    )
    producer_nodes = [node for node in layer.nodes if node.node_type == "artist"]
    assert len(producer_nodes) == 1
    assert producer_nodes[0].node_key == artist_key(producer_id)


def test_solo_artist_album_is_included_without_type_filter() -> None:
    album = _album(band_type="person")
    producer_id = uuid.uuid4()
    layer = build_producer_album_layer(_data([album], [_row(producer_id, album)]))
    album_node = next(node for node in layer.nodes if node.node_type == "album")
    assert album_node.attributes["band_type"] == "person"
    assert album_node.attributes["year"] == 1991
    assert album_node.attributes["decade"] == "1990s"


def test_simple_graph_collapses_roles_but_persists_role_edges() -> None:
    album = _album()
    producer_id = uuid.uuid4()
    layer = build_producer_album_layer(
        _data(
            [album],
            [
                _row(producer_id, album, role="producer", ratio=1.0),
                _row(producer_id, album, role="co-producer", ratio=0.5),
            ],
        )
    )
    assert len(layer.edges) == 2
    assert {edge.role_code for edge in layer.edges} == {"producer", "co-producer"}
    source = artist_key(producer_id)
    target = album_key(album.album_id)
    assert layer.graph.number_of_edges(source, target) == 1
    assert layer.graph[source][target]["support_ratio"] == 1.0
