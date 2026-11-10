from __future__ import annotations

import uuid
from datetime import date

from hmde.network.graph import (
    PRODUCER_ALBUM,
    PRODUCER_BAND,
    build_producer_album_layer,
    build_producer_band_layer,
)
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary
from hmde.network.metrics import compute_metrics


def _album(*, band_id: uuid.UUID, year: int = 1991) -> AlbumRow:
    return AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title="Album",
        first_release_date=date(year, 1, 1),
        band_id=band_id,
        band_name="Band",
        band_mbid=str(uuid.uuid4()),
        band_type="group",
        band_country="US",
        primary_code="heavy-metal",
        primary_status="approved",
    )


def _row(producer_id: uuid.UUID, album: AlbumRow, *, ratio: float = 1.0) -> ProducerAlbumRoleRow:
    return ProducerAlbumRoleRow(
        producer_id=producer_id,
        producer_name="Producer",
        producer_mbid=str(uuid.uuid4()),
        producer_type="person",
        producer_country="GB",
        album_id=album.album_id,
        role_code="producer",
        supporting_recordings=1,
        album_recordings=2,
        support_ratio=ratio,
        has_release_group_scope=ratio == 1.0,
        scope_mix={"release_group": 1},
        evidence={"credit_ids": [], "source_record_ids": []},
    )


def _layers() -> tuple[NetworkData, object, object]:
    band_id = uuid.uuid4()
    album = _album(band_id=band_id)
    producer = uuid.uuid4()
    data = NetworkData(
        albums={album.album_id: album},
        producer_albums=(_row(producer, album, ratio=0.5),),
        quality=QualitySummary({}, 0, 0, 0, ()),
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    return data, album_layer, band_layer


def test_view_contract_exposes_type_year_roles_support_and_evidence() -> None:
    _, album_layer, band_layer = _layers()
    producer_node = next(node for node in album_layer.nodes if node.roles == ("producer",))
    album_node = next(node for node in album_layer.nodes if node.node_type == "album")
    band_node = next(node for node in band_layer.nodes if node.roles == ("band",))
    assert producer_node.attributes["artist_type"] == "person"
    assert album_node.attributes["year"] == 1991
    assert album_node.attributes["decade"] == "1990s"
    assert band_node.attributes["band_type"] == "group"
    album_edge = album_layer.edges[0]
    assert album_edge.layer_code == PRODUCER_ALBUM
    assert album_edge.support_ratio == 0.5
    assert album_edge.role_code == "producer"
    band_edge = band_layer.edges[0]
    assert band_edge.layer_code == PRODUCER_BAND
    assert band_edge.evidence["album_count"] == 1
    assert band_edge.evidence["album_ids"]


def test_top_k_does_not_truncate_graph_data() -> None:
    data, album_layer, band_layer = _layers()
    small = compute_metrics(data, album_layer, band_layer, top_k=1)
    large = compute_metrics(data, album_layer, band_layer, top_k=20)
    assert small.graph_counts == large.graph_counts
    assert len(small.top_albums) == 1
    assert len(large.top_albums) == 1
    assert len(small.node_metrics) == len(large.node_metrics)
