from __future__ import annotations

import uuid
from datetime import date

from hmde.network.graph import build_producer_album_layer, build_producer_band_layer
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary
from hmde.network.metrics import compute_metrics


def _album(year: int | None) -> AlbumRow:
    return AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title="Album",
        first_release_date=date(year, 1, 1) if year else None,
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
        producer_name="Producer",
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


def test_temporal_metrics_use_decades_and_exclude_unknown_dates() -> None:
    producer = uuid.uuid4()
    album_1991 = _album(1991)
    album_2001 = _album(2001)
    album_unknown = _album(None)
    data = NetworkData(
        albums={album.album_id: album for album in (album_1991, album_2001, album_unknown)},
        producer_albums=(
            _row(producer, album_1991),
            _row(producer, album_2001),
            _row(producer, album_unknown),
        ),
        quality=QualitySummary({}, 0, 0, 1, ()),
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    payload = compute_metrics(data, album_layer, band_layer)
    decades = {
        metric.scope_key for metric in payload.temporal_metrics if metric.scope_type == "decade"
    }
    assert decades == {"1990s", "2000s"}
    assert not any(
        metric.scope_key == "unknown" and metric.scope_type == "decade"
        for metric in payload.temporal_metrics
    )
