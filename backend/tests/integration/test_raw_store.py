from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select

from hmde.etl.musicbrainz.raw_store import (
    RawPayloadCorruptionError,
    RawPayloadMissingError,
    RawStore,
)
from hmde.models import IngestError, IngestRun, RawResponse


@pytest.fixture
def ingest_run_id(seeded_session_factory):
    run_id = uuid.uuid4()
    with seeded_session_factory() as session:
        session.add(
            IngestRun(
                id=run_id,
                seed_list_version="0.1.0",
                code_version="test",
            )
        )
        session.commit()

    try:
        yield run_id
    finally:
        with seeded_session_factory() as session:
            session.execute(delete(RawResponse).where(RawResponse.first_ingest_run_id == run_id))
            session.execute(delete(IngestError).where(IngestError.ingest_run_id == run_id))
            session.execute(delete(IngestRun).where(IngestRun.id == run_id))
            session.commit()


def _store_response(session, root, run_id, *, body: bytes, fetched_at: datetime) -> RawResponse:
    return RawStore(session, root).store_response(
        ingest_run_id=run_id,
        source="musicbrainz",
        source_entity_type="artist",
        external_id="artist-mbid",
        method="GET",
        request_url="https://musicbrainz.org/ws/2/artist/artist-mbid",
        request_params={"inc": "url-rels", "fmt": "json"},
        fetched_at=fetched_at,
        http_status=200,
        body=body,
        license="CC0-1.0",
        api_version="2",
    )


def test_raw_store_persists_and_reuses_cached_response(
    seeded_session_factory,
    ingest_run_id,
    tmp_path,
) -> None:
    fetched_at = datetime.now(UTC)

    with seeded_session_factory() as session:
        first = _store_response(
            session, tmp_path, ingest_run_id, body=b'{"x": 1}', fetched_at=fetched_at
        )
        session.commit()
        first_id = first.id
        request_key = first.request_key
        raw_path = first.raw_path

    with seeded_session_factory() as session:
        second = _store_response(
            session,
            tmp_path,
            ingest_run_id,
            body=b'{"x": 1}',
            fetched_at=fetched_at + timedelta(seconds=1),
        )
        session.commit()

        assert second.id == first_id
        count = session.scalar(
            select(func.count())
            .select_from(RawResponse)
            .where(RawResponse.first_ingest_run_id == ingest_run_id)
        )
        assert count == 1
        assert (tmp_path / raw_path).read_bytes() == b'{"x": 1}'
        assert not raw_path.startswith("/")
        assert session.scalar(select(RawResponse).where(RawResponse.id == first_id)) is not None
        assert request_key == second.request_key


def test_raw_store_keeps_changed_payload_and_cache_returns_latest(
    seeded_session_factory,
    ingest_run_id,
    tmp_path,
) -> None:
    first_time = datetime.now(UTC)

    with seeded_session_factory() as session:
        first = _store_response(
            session,
            tmp_path,
            ingest_run_id,
            body=b'{"version": 1}',
            fetched_at=first_time,
        )
        session.commit()
        request_key = first.request_key
        first_path = first.raw_path

    with seeded_session_factory() as session:
        second = _store_response(
            session,
            tmp_path,
            ingest_run_id,
            body=b'{"version": 2}',
            fetched_at=first_time + timedelta(seconds=1),
        )
        session.commit()
        second_id = second.id
        second_path = second.raw_path

        count = session.scalar(
            select(func.count())
            .select_from(RawResponse)
            .where(RawResponse.first_ingest_run_id == ingest_run_id)
        )
        assert count == 2
        assert first_path != second_path

    with seeded_session_factory() as session:
        cached = RawStore(session, tmp_path).get_cached(request_key)
        assert cached is not None
        assert cached.id == second_id
        assert RawStore(session, tmp_path).read_payload(cached) == b'{"version": 2}'


def test_raw_store_detects_missing_and_corrupt_cache(
    seeded_session_factory,
    ingest_run_id,
    tmp_path,
) -> None:
    with seeded_session_factory() as session:
        raw = _store_response(
            session,
            tmp_path,
            ingest_run_id,
            body=b'{"x": 1}',
            fetched_at=datetime.now(UTC),
        )
        session.commit()
        request_key = raw.request_key
        raw_path = tmp_path / raw.raw_path

    raw_path.write_bytes(b"tampered")
    with seeded_session_factory() as session:
        with pytest.raises(RawPayloadCorruptionError):
            RawStore(session, tmp_path).get_cached(request_key)

    raw_path.unlink()
    with seeded_session_factory() as session:
        with pytest.raises(RawPayloadMissingError):
            RawStore(session, tmp_path).get_cached(request_key)
