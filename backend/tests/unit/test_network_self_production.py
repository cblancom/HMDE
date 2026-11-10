from __future__ import annotations

import uuid
from datetime import date

from hmde.network.graph import artist_key, build_producer_album_layer, build_producer_band_layer
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary


def test_self_produced_album_has_one_node_no_self_loop_and_explicit_count() -> None:
    band_id = uuid.uuid4()
    album = AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title="Self-produced",
        first_release_date=date(1994, 1, 1),
        band_id=band_id,
        band_name="Self Band",
        band_mbid=str(uuid.uuid4()),
        band_type="group",
        band_country="US",
        primary_code="heavy-metal",
        primary_status="approved",
    )
    row = ProducerAlbumRoleRow(
        producer_id=band_id,
        producer_name="Self Band",
        producer_mbid=album.band_mbid,
        producer_type="group",
        producer_country="US",
        album_id=album.album_id,
        role_code="producer",
        supporting_recordings=1,
        album_recordings=1,
        support_ratio=1.0,
        has_release_group_scope=True,
        scope_mix={"release_group": 1},
        evidence={"credit_ids": [], "source_record_ids": []},
    )
    data = NetworkData(
        albums={album.album_id: album},
        producer_albums=(row,),
        quality=QualitySummary({}, 0, 0, 0, ()),
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    node = next(node for node in band_layer.nodes if node.node_key == artist_key(band_id))
    assert set(node.roles) == {"band", "producer"}
    assert node.attributes["self_produced_albums"] == 1
    assert band_layer.edges == ()
    assert band_layer.self_produced_albums == {band_id: 1}
