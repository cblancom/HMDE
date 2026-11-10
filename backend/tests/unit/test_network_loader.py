from __future__ import annotations

import uuid
from datetime import date

from hmde.network.loader import AlbumRow, aggregate_producer_albums


def _album(album_id: uuid.UUID) -> AlbumRow:
    return AlbumRow(
        album_id=album_id,
        album_mbid=str(uuid.uuid4()),
        album_title="Album",
        first_release_date=date(1990, 1, 1),
        band_id=uuid.uuid4(),
        band_name="Band",
        band_mbid=str(uuid.uuid4()),
        band_type="group",
        band_country="US",
        primary_code="heavy-metal",
        primary_status="approved",
    )


def _credit(producer_id: uuid.UUID, album_id: uuid.UUID, **overrides):
    values = {
        "credit_id": uuid.uuid4(),
        "producer_id": producer_id,
        "producer_name": "Producer",
        "producer_mbid": str(uuid.uuid4()),
        "producer_type": "person",
        "producer_country": "GB",
        "role_code": "producer",
        "scope": "recording",
        "album_id": album_id,
        "release_id": None,
        "recording_id": uuid.uuid4(),
        "credited_as": None,
        "confidence": 1.0,
        "status": "confirmed",
        "source_record_id": uuid.uuid4(),
    }
    values.update(overrides)
    return values


def test_release_group_scope_is_full_album_support() -> None:
    album_id = uuid.uuid4()
    producer_id = uuid.uuid4()
    rows = aggregate_producer_albums(
        {album_id: _album(album_id)},
        [_credit(producer_id, album_id, scope="release_group", recording_id=None)],
        album_recordings={album_id: {uuid.uuid4(), uuid.uuid4()}},
        release_recordings={},
    )
    assert len(rows) == 1
    assert rows[0].support_ratio == 1.0
    assert rows[0].has_release_group_scope is True
    assert rows[0].scope_mix == {"release_group": 1}


def test_recording_scope_uses_observed_ratio() -> None:
    album_id = uuid.uuid4()
    producer_id = uuid.uuid4()
    recording = uuid.uuid4()
    rows = aggregate_producer_albums(
        {album_id: _album(album_id)},
        [_credit(producer_id, album_id, recording_id=recording)],
        album_recordings={album_id: {recording, uuid.uuid4()}},
        release_recordings={},
    )
    assert rows[0].supporting_recordings == 1
    assert rows[0].album_recordings == 2
    assert rows[0].support_ratio == 0.5


def test_release_scope_uses_release_recordings() -> None:
    album_id = uuid.uuid4()
    producer_id = uuid.uuid4()
    release_id = uuid.uuid4()
    recordings = {uuid.uuid4(), uuid.uuid4()}
    rows = aggregate_producer_albums(
        {album_id: _album(album_id)},
        [
            _credit(
                producer_id,
                album_id,
                scope="release",
                release_id=release_id,
                recording_id=None,
            )
        ],
        album_recordings={album_id: recordings},
        release_recordings={release_id: recordings},
    )
    assert rows[0].supporting_recordings == 2
    assert rows[0].support_ratio == 1.0


def test_missing_denominator_leaves_ratio_null() -> None:
    album_id = uuid.uuid4()
    producer_id = uuid.uuid4()
    rows = aggregate_producer_albums(
        {album_id: _album(album_id)},
        [_credit(producer_id, album_id)],
        album_recordings={},
        release_recordings={},
    )
    assert rows[0].support_ratio is None
