from __future__ import annotations

import uuid
from datetime import date

from hmde.network.graph import build_producer_album_layer, build_producer_band_layer
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary
from hmde.network.metrics import compute_metrics


def _album(band_id: uuid.UUID, year: int = 1991) -> AlbumRow:
    return AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title=f"Album {year}",
        first_release_date=date(year, 1, 1),
        band_id=band_id,
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
        producer_name=f"Producer {producer_id}",
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


def _data(albums: list[AlbumRow], rows: list[ProducerAlbumRoleRow]) -> NetworkData:
    return NetworkData(
        albums={album.album_id: album for album in albums},
        producer_albums=tuple(rows),
        quality=QualitySummary({}, 0, 0, 0, ()),
    )


def test_computes_counts_degrees_and_concentration() -> None:
    band_a = uuid.uuid4()
    band_b = uuid.uuid4()
    album_a1 = _album(band_a, 1991)
    album_a2 = _album(band_a, 1992)
    album_b1 = _album(band_b, 1993)
    producer_a = uuid.uuid4()
    producer_b = uuid.uuid4()
    data = _data(
        [album_a1, album_a2, album_b1],
        [
            _row(producer_a, album_a1),
            _row(producer_a, album_a2),
            _row(producer_b, album_b1),
        ],
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    payload = compute_metrics(data, album_layer, band_layer, top_k=10)

    producer_metrics = {
        (metric.producer_id, metric.metric_code): metric.value
        for metric in payload.producer_metrics
    }
    assert producer_metrics[(producer_a, "NA-PROD-001")] == 2
    assert producer_metrics[(producer_b, "NA-PROD-001")] == 1
    assert producer_metrics[(producer_a, "NA-PROD-002")] == 1
    assert producer_metrics[(producer_b, "NA-PROD-002")] == 1

    top = payload.top_albums[0]
    assert top["producer_id"] == str(producer_a)
    assert top["count"] == 2

    node_degrees = {
        (metric.node_key, metric.layer_code, metric.metric_code): metric.value
        for metric in payload.node_metrics
    }
    assert node_degrees[(f"artist:{producer_a}", "producer_album", "NA-DEG-001")] == 2
    assert payload.graph_counts["producer_album"]["components"] == 2
    assert payload.support_summary == {"full": 3, "partial": 0, "unknown": 0}
