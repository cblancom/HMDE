from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from hmde.core.config import Settings
from hmde.etl.musicbrainz.client import (
    MUSICBRAINZ_API_VERSION,
    MusicBrainzCacheMissError,
    MusicBrainzClient,
    MusicBrainzHTTPError,
    MusicBrainzRequestError,
    MusicBrainzResponseError,
)
from hmde.etl.musicbrainz.raw_store import build_request_key, hash_payload
from hmde.models import RawResponse

BASE_URL = "https://mb.test/ws/2/"
USER_AGENT = "HMDE/0.1 (test@example.test)"
INGEST_RUN_ID = uuid.uuid4()


class FakeLimiter:
    def __init__(self) -> None:
        self.calls = 0

    def wait(self) -> None:
        self.calls += 1


class FakeRawStore:
    def __init__(self) -> None:
        self.rows: list[RawResponse] = []
        self.payloads: dict[uuid.UUID, bytes] = {}

    def get_cached(self, request_key: str) -> RawResponse | None:
        return next(
            (row for row in reversed(self.rows) if row.request_key == request_key),
            None,
        )

    def read_payload(self, raw_response: RawResponse) -> bytes:
        return self.payloads[raw_response.id]

    def store_response(self, **kwargs: Any) -> RawResponse:
        body = kwargs.pop("body")
        request_params = kwargs.pop("request_params")
        payload_hash = hash_payload(body)
        request_key = build_request_key(
            kwargs["method"],
            kwargs["request_url"],
            request_params,
            kwargs["api_version"],
        )

        existing = next(
            (
                row
                for row in self.rows
                if row.request_key == request_key and row.payload_hash == payload_hash
            ),
            None,
        )
        if existing is not None:
            return existing

        raw = RawResponse(
            id=uuid.uuid4(),
            first_ingest_run_id=kwargs["ingest_run_id"],
            source=kwargs["source"],
            source_entity_type=kwargs["source_entity_type"],
            external_id=kwargs["external_id"],
            request_key=request_key,
            request_url=kwargs["request_url"],
            request_params=request_params,
            fetched_at=kwargs["fetched_at"],
            http_status=kwargs["http_status"],
            payload_hash=payload_hash,
            raw_path=f"{payload_hash}.json",
            license=kwargs["license"],
            api_version=kwargs["api_version"],
        )
        self.rows.append(raw)
        self.payloads[raw.id] = body
        return raw


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde",
        musicbrainz_user_agent=USER_AGENT,
        musicbrainz_base_url="https://mb.test/ws/2",
        musicbrainz_timeout_seconds=5.0,
        musicbrainz_min_interval_seconds=1.0,
    )


def _client(
    handler,
    *,
    raw_store: FakeRawStore | None = None,
    cache_only: bool = False,
    refresh: bool = False,
    sleeps: list[float] | None = None,
) -> tuple[MusicBrainzClient, FakeRawStore, FakeLimiter]:
    store = raw_store or FakeRawStore()
    limiter = FakeLimiter()
    http_client = httpx.Client(
        base_url=BASE_URL,
        transport=httpx.MockTransport(handler),
    )
    sleep_log = sleeps if sleeps is not None else []
    client = MusicBrainzClient(
        settings=_settings(),
        raw_store=store,  # type: ignore[arg-type]
        ingest_run_id=INGEST_RUN_ID,
        cache_only=cache_only,
        refresh=refresh,
        http_client=http_client,
        rate_limiter=limiter,  # type: ignore[arg-type]
        sleep=sleep_log.append,
        jitter=lambda: 0.0,
    )
    return client, store, limiter


def _raw_response(request_url: str, body: bytes, fetched_at: datetime | None = None) -> RawResponse:
    params = {"fmt": "json"}
    payload_hash = hash_payload(body)
    return RawResponse(
        id=uuid.uuid4(),
        first_ingest_run_id=INGEST_RUN_ID,
        source="musicbrainz",
        source_entity_type="artist",
        external_id="abc",
        request_key=build_request_key("GET", request_url, params, MUSICBRAINZ_API_VERSION),
        request_url=request_url,
        request_params=params,
        fetched_at=fetched_at or datetime.now(UTC),
        http_status=200,
        payload_hash=payload_hash,
        raw_path=f"{payload_hash}.json",
        license="CC0-1.0",
        api_version=MUSICBRAINZ_API_VERSION,
    )


def test_successful_request_sends_headers_and_stores_raw_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://mb.test/ws/2/artist/abc?fmt=json&inc=url-rels")
        assert request.headers["User-Agent"] == USER_AGENT
        assert request.headers["Accept"] == "application/json"
        return httpx.Response(200, json={"id": "abc"})

    client, store, limiter = _client(handler)

    result = client.fetch_json(
        "artist/abc",
        params={"inc": "url-rels"},
        source_entity_type="artist",
        external_id="abc",
    )

    assert result.data == {"id": "abc"}
    assert result.from_cache is False
    assert len(store.rows) == 1
    assert store.rows[0].request_url == "https://mb.test/ws/2/artist/abc"
    assert limiter.calls == 1


def test_cache_hit_avoids_network_and_rate_limit() -> None:
    request_url = "https://mb.test/ws/2/artist/abc"
    body = b'{"cached": true}'
    raw = _raw_response(request_url, body)
    store = FakeRawStore()
    store.rows.append(raw)
    store.payloads[raw.id] = body

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used on a cache hit")

    client, _, limiter = _client(handler, raw_store=store, cache_only=True)

    result = client.fetch_json(
        "artist/abc",
        source_entity_type="artist",
        external_id="abc",
    )

    assert result.data == {"cached": True}
    assert result.from_cache is True
    assert limiter.calls == 0


def test_cache_only_miss_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used in cache-only mode")

    client, _, _ = _client(handler, cache_only=True)

    with pytest.raises(MusicBrainzCacheMissError):
        client.fetch_json(
            "artist/abc",
            source_entity_type="artist",
            external_id="abc",
        )


def test_429_honours_retry_after_then_succeeds() -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "slow down"}),
            httpx.Response(200, json={"id": "abc"}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    sleeps: list[float] = []
    client, _, limiter = _client(handler, sleeps=sleeps)

    result = client.fetch_json(
        "artist/abc",
        source_entity_type="artist",
        external_id="abc",
    )

    assert result.data == {"id": "abc"}
    assert sleeps == [2.0]
    assert limiter.calls == 2


def test_500_exhausts_retries_and_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server"})

    sleeps: list[float] = []
    client, _, limiter = _client(handler, sleeps=sleeps)

    with pytest.raises(MusicBrainzHTTPError) as exc_info:
        client.fetch_json(
            "artist/abc",
            source_entity_type="artist",
            external_id="abc",
        )

    assert exc_info.value.status_code == 500
    assert sleeps == [0.5, 1.0]
    assert limiter.calls == 3


def test_non_retryable_4xx_raises_immediately() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    sleeps: list[float] = []
    client, _, limiter = _client(handler, sleeps=sleeps)

    with pytest.raises(MusicBrainzHTTPError) as exc_info:
        client.fetch_json(
            "artist/abc",
            source_entity_type="artist",
            external_id="abc",
        )

    assert exc_info.value.status_code == 404
    assert sleeps == []
    assert limiter.calls == 1


def test_transport_timeout_exhausts_retries_and_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    sleeps: list[float] = []
    client, _, limiter = _client(handler, sleeps=sleeps)

    with pytest.raises(MusicBrainzRequestError):
        client.fetch_json(
            "artist/abc",
            source_entity_type="artist",
            external_id="abc",
        )

    assert sleeps == [0.5, 1.0]
    assert limiter.calls == 3


def test_invalid_json_raises_without_raw_persistence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client, store, limiter = _client(handler)

    with pytest.raises(MusicBrainzResponseError):
        client.fetch_json(
            "artist/abc",
            source_entity_type="artist",
            external_id="abc",
        )

    assert store.rows == []
    assert limiter.calls == 1


def test_client_requires_user_agent() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde",
        musicbrainz_user_agent=None,
    )

    with pytest.raises(ValueError, match="MUSICBRAINZ_USER_AGENT"):
        MusicBrainzClient(
            settings=settings,
            raw_store=FakeRawStore(),  # type: ignore[arg-type]
            ingest_run_id=INGEST_RUN_ID,
        )


def test_cache_only_client_allows_missing_user_agent() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde",
        musicbrainz_user_agent=None,
    )
    http_client = httpx.Client(
        base_url=BASE_URL,
        transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(AssertionError("no network"))
        ),
    )
    client = MusicBrainzClient(
        settings=settings,
        raw_store=FakeRawStore(),  # type: ignore[arg-type]
        ingest_run_id=INGEST_RUN_ID,
        cache_only=True,
        http_client=http_client,
    )
    client.close()
    http_client.close()
