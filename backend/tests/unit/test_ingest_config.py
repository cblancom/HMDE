from __future__ import annotations

import pytest

from hmde.core.config import load_settings

DATABASE_URL = "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde"


def test_musicbrainz_settings_use_defaults() -> None:
    settings = load_settings({"DATABASE_URL": DATABASE_URL})

    assert settings.musicbrainz_user_agent is None
    assert settings.musicbrainz_base_url == "https://musicbrainz.org/ws/2"
    assert settings.musicbrainz_timeout_seconds == 30.0
    assert settings.musicbrainz_min_interval_seconds == 1.0


def test_musicbrainz_settings_read_environment_values() -> None:
    settings = load_settings(
        {
            "DATABASE_URL": DATABASE_URL,
            "MUSICBRAINZ_USER_AGENT": "HMDE/0.1 (dev@example.test)",
            "MUSICBRAINZ_BASE_URL": "https://example.test/ws/2/",
            "MUSICBRAINZ_TIMEOUT_SECONDS": "12.5",
            "MUSICBRAINZ_MIN_INTERVAL_SECONDS": "2",
        }
    )

    assert settings.musicbrainz_user_agent == "HMDE/0.1 (dev@example.test)"
    assert settings.musicbrainz_base_url == "https://example.test/ws/2"
    assert settings.musicbrainz_timeout_seconds == 12.5
    assert settings.musicbrainz_min_interval_seconds == 2.0


@pytest.mark.parametrize("key", ["MUSICBRAINZ_TIMEOUT_SECONDS", "MUSICBRAINZ_MIN_INTERVAL_SECONDS"])
def test_musicbrainz_numeric_settings_reject_invalid_values(key: str) -> None:
    with pytest.raises(RuntimeError, match=key):
        load_settings({"DATABASE_URL": DATABASE_URL, key: "not-a-number"})


@pytest.mark.parametrize("value", ["0", "-1"])
def test_musicbrainz_numeric_settings_must_be_positive(value: str) -> None:
    with pytest.raises(RuntimeError, match="greater than zero"):
        load_settings({"DATABASE_URL": DATABASE_URL, "MUSICBRAINZ_TIMEOUT_SECONDS": value})


def test_musicbrainz_minimum_interval_cannot_bypass_rate_limit() -> None:
    with pytest.raises(RuntimeError, match="at least 1.0"):
        load_settings(
            {
                "DATABASE_URL": DATABASE_URL,
                "MUSICBRAINZ_MIN_INTERVAL_SECONDS": "0.5",
            }
        )
