"""Synchronous MusicBrainz API client."""

from __future__ import annotations

import json
import random
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from hmde.core.config import Settings
from hmde.etl.musicbrainz.rate_limit import RateLimiter
from hmde.etl.musicbrainz.raw_store import (
    RawPayloadCorruptionError,
    RawPayloadMissingError,
    RawStore,
    build_request_key,
)
from hmde.models import RawResponse

MUSICBRAINZ_API_VERSION = "2"
MUSICBRAINZ_LICENSE = "CC0-1.0"
MAX_ATTEMPTS = 3


class MusicBrainzError(Exception):
    """Base error for MusicBrainz client operations."""


class MusicBrainzCacheMissError(MusicBrainzError):
    """A cache-only request has no stored payload."""


class MusicBrainzHTTPError(MusicBrainzError):
    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"MusicBrainz request failed with status {status_code}: {url}")


class MusicBrainzRequestError(MusicBrainzError):
    """A request failed after exhausting retries."""


class MusicBrainzResponseError(MusicBrainzError):
    """A response was not valid JSON or not a JSON object."""


@dataclass(frozen=True, slots=True)
class MusicBrainzResponse:
    data: dict[str, Any]
    raw_response: RawResponse
    from_cache: bool


class MusicBrainzClient:
    def __init__(
        self,
        *,
        settings: Settings,
        raw_store: RawStore,
        ingest_run_id: uuid.UUID,
        cache_only: bool = False,
        refresh: bool = False,
        http_client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        if not cache_only and not settings.musicbrainz_user_agent:
            raise ValueError("MUSICBRAINZ_USER_AGENT is required for live ingestion")
        if cache_only and refresh:
            raise ValueError("cache_only and refresh are mutually exclusive")

        self._settings = settings
        self._raw_store = raw_store
        self._ingest_run_id = ingest_run_id
        self._cache_only = cache_only
        self._refresh = refresh
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(
            base_url=f"{settings.musicbrainz_base_url.rstrip('/')}/",
            timeout=settings.musicbrainz_timeout_seconds,
        )
        self._rate_limiter = rate_limiter or RateLimiter(settings.musicbrainz_min_interval_seconds)
        self._sleep = sleep
        self._jitter = jitter

    @property
    def request_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": self._settings.musicbrainz_user_agent or "",
        }

    def fetch_json(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        source_entity_type: str,
        external_id: str,
    ) -> MusicBrainzResponse:
        request_params = {"fmt": "json", **dict(params or {})}
        request_url = str(self._http.base_url.join(path.lstrip("/")))
        request_key = build_request_key(
            "GET",
            request_url,
            request_params,
            MUSICBRAINZ_API_VERSION,
        )

        if not self._refresh:
            cached = self._cached_response(request_key)
            if cached is not None:
                return cached

        if self._cache_only:
            raise MusicBrainzCacheMissError(f"no cached response for request key {request_key}")

        response = self._request_with_retries(path, request_params)
        body = response.content
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise MusicBrainzResponseError(
                f"MusicBrainz returned invalid JSON: {request_url}"
            ) from exc
        if not isinstance(data, dict):
            raise MusicBrainzResponseError(
                f"MusicBrainz returned a non-object JSON response: {request_url}"
            )

        fetched_at = datetime.now(UTC)
        raw_response = self._raw_store.store_response(
            ingest_run_id=self._ingest_run_id,
            source="musicbrainz",
            source_entity_type=source_entity_type,
            external_id=external_id,
            method="GET",
            request_url=request_url,
            request_params=request_params,
            fetched_at=fetched_at,
            http_status=response.status_code,
            body=body,
            license=MUSICBRAINZ_LICENSE,
            api_version=MUSICBRAINZ_API_VERSION,
        )
        return MusicBrainzResponse(data=data, raw_response=raw_response, from_cache=False)

    def _cached_response(self, request_key: str) -> MusicBrainzResponse | None:
        try:
            raw_response = self._raw_store.get_cached(request_key)
            if raw_response is None:
                return None
            body = self._raw_store.read_payload(raw_response)
        except (RawPayloadMissingError, RawPayloadCorruptionError):
            if self._cache_only:
                raise
            return None

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            if self._cache_only:
                raise MusicBrainzResponseError(
                    "cached MusicBrainz payload is not valid JSON"
                ) from exc
            return None
        if not isinstance(data, dict):
            if self._cache_only:
                raise MusicBrainzResponseError("cached MusicBrainz payload is not a JSON object")
            return None
        return MusicBrainzResponse(data=data, raw_response=raw_response, from_cache=True)

    def _request_with_retries(
        self,
        path: str,
        params: Mapping[str, Any],
    ) -> httpx.Response:
        last_request_error: httpx.RequestError | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._rate_limiter.wait()
            try:
                response = self._http.get(
                    path.lstrip("/"),
                    params=params,
                    headers=self.request_headers,
                )
            except httpx.RequestError as exc:
                last_request_error = exc
                if attempt == MAX_ATTEMPTS:
                    break
                self._sleep(self._backoff(attempt))
                continue

            if 200 <= response.status_code < 300:
                return response

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt == MAX_ATTEMPTS:
                    raise MusicBrainzHTTPError(
                        response.status_code,
                        str(response.request.url),
                    )
                retry_after = self._retry_after_seconds(response)
                self._sleep(retry_after if retry_after is not None else self._backoff(attempt))
                continue

            raise MusicBrainzHTTPError(response.status_code, str(response.request.url))

        raise MusicBrainzRequestError(
            f"MusicBrainz request failed after {MAX_ATTEMPTS} attempts"
        ) from last_request_error

    def _backoff(self, attempt: int) -> float:
        base = 0.5 * (2 ** (attempt - 1))
        return base + (self._jitter() * 0.25)

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            seconds = float(value)
        except ValueError:
            return None
        return seconds if seconds >= 0 else None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> MusicBrainzClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
