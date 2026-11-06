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


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if env is None else env

    database_url = values.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required and must not be empty")

    app_env = values.get("APP_ENV", "development").strip() or "development"
    log_level = values.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    test_database_url = values.get("TEST_DATABASE_URL", "").strip() or None

    return Settings(
        database_url=database_url,
        app_env=app_env,
        log_level=log_level,
        test_database_url=test_database_url,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
