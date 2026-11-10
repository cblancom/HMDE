"""Environment configuration for the HMDE backend."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    app_env: str = "development"
    log_level: str = "INFO"
    test_database_url: str | None = None
    musicbrainz_user_agent: str | None = None
    musicbrainz_base_url: str = "https://musicbrainz.org/ws/2"
    musicbrainz_timeout_seconds: float = 30.0
    musicbrainz_min_interval_seconds: float = 1.0
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if env is None else env

    database_url = values.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required and must not be empty")

    app_env = values.get("APP_ENV", "development").strip() or "development"
    log_level = values.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    test_database_url = values.get("TEST_DATABASE_URL", "").strip() or None
    musicbrainz_user_agent = values.get("MUSICBRAINZ_USER_AGENT", "").strip() or None
    musicbrainz_base_url = (
        values.get("MUSICBRAINZ_BASE_URL", "").strip().rstrip("/") or "https://musicbrainz.org/ws/2"
    )
    musicbrainz_timeout_seconds = _positive_float(values, "MUSICBRAINZ_TIMEOUT_SECONDS", 30.0)
    musicbrainz_min_interval_seconds = _positive_float(
        values, "MUSICBRAINZ_MIN_INTERVAL_SECONDS", 1.0
    )
    cors_origins = _origins(values.get("CORS_ORIGINS", ""))
    if musicbrainz_min_interval_seconds < 1.0:
        raise RuntimeError(
            "MUSICBRAINZ_MIN_INTERVAL_SECONDS must be at least 1.0 to respect "
            "MusicBrainz rate limits"
        )

    return Settings(
        database_url=database_url,
        app_env=app_env,
        log_level=log_level,
        test_database_url=test_database_url,
        musicbrainz_user_agent=musicbrainz_user_agent,
        musicbrainz_base_url=musicbrainz_base_url,
        musicbrainz_timeout_seconds=musicbrainz_timeout_seconds,
        musicbrainz_min_interval_seconds=musicbrainz_min_interval_seconds,
        cors_origins=cors_origins,
    )


def _origins(raw: str) -> tuple[str, ...]:
    values = tuple(item.strip().rstrip("/") for item in raw.split(",") if item.strip())
    return values or ("http://localhost:5173", "http://127.0.0.1:5173")


def _positive_float(values: Mapping[str, str], key: str, default: float) -> float:
    raw = values.get(key, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{key} must be a number") from exc
    if value <= 0:
        raise RuntimeError(f"{key} must be greater than zero")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
