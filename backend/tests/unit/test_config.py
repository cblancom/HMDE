from __future__ import annotations

import pytest

from hmde.core.config import get_settings, load_settings


def test_load_settings_reads_environment_values() -> None:
    settings = load_settings(
        {
            "DATABASE_URL": "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde",
            "APP_ENV": "test",
            "LOG_LEVEL": "debug",
            "TEST_DATABASE_URL": "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde_test",
        }
    )

    assert settings.database_url == "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde"
    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.test_database_url == (
        "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde_test"
    )


def test_load_settings_uses_defaults() -> None:
    settings = load_settings(
        {"DATABASE_URL": "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde"}
    )

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.test_database_url is None


@pytest.mark.parametrize("database_url", [None, "", "   "])
def test_load_settings_requires_database_url(database_url: str | None) -> None:
    env = {} if database_url is None else {"DATABASE_URL": database_url}

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        load_settings(env)


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde")

    first = get_settings()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://hmde:hmde_dev@localhost:5433/other")
    second = get_settings()

    assert first is second
    get_settings.cache_clear()
