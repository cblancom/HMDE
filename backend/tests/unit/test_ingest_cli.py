from __future__ import annotations

from pathlib import Path

import pytest

from hmde.core.config import get_settings
from hmde.etl.musicbrainz import cli


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_help_works_without_runtime_settings(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MUSICBRAINZ_USER_AGENT", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    assert exc_info.value.code == 0


def test_live_ingestion_requires_user_agent(monkeypatch, capsys) -> None:
    monkeypatch.delenv("MUSICBRAINZ_USER_AGENT", raising=False)

    result = cli.main(["ingest"])

    assert result == 1
    assert "MUSICBRAINZ_USER_AGENT is required" in capsys.readouterr().err


def test_cache_only_allows_missing_user_agent(monkeypatch) -> None:
    monkeypatch.delenv("MUSICBRAINZ_USER_AGENT", raising=False)
    calls: list[cli.IngestOptions] = []
    monkeypatch.setattr(cli, "run_ingest", lambda options, settings: calls.append(options) or 0)

    result = cli.main(["ingest", "--cache-only"])

    assert result == 0
    assert calls[0].cache_only is True
    assert calls[0].refresh is False


def test_live_ingestion_passes_options_to_runner(monkeypatch) -> None:
    monkeypatch.setenv("MUSICBRAINZ_USER_AGENT", "HMDE/0.1 (dev@example.test)")
    calls: list[cli.IngestOptions] = []
    monkeypatch.setattr(cli, "run_ingest", lambda options, settings: calls.append(options) or 0)

    result = cli.main(
        [
            "ingest",
            "--seed-list",
            "../data/seed-list.json",
            "--output",
            "../data/ingestions/musicbrainz",
            "--band",
            "00000000-0000-0000-0000-000000000001",
            "--max-bands",
            "2",
        ]
    )

    assert result == 0
    assert calls[0].seed_list == Path("../data/seed-list.json")
    assert calls[0].output == Path("../data/ingestions/musicbrainz")
    assert calls[0].bands == ("00000000-0000-0000-0000-000000000001",)
    assert calls[0].max_bands == 2
    assert calls[0].cache_only is False


def test_cache_only_and_refresh_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.build_parser().parse_args(["ingest", "--cache-only", "--refresh"])

    assert exc_info.value.code == 2
