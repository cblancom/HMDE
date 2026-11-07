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


def test_cli_parses_raw_root_and_modes(tmp_path: Path) -> None:
    args = cli.build_parser().parse_args(
        [
            "ingest",
            "--raw-root",
            str(tmp_path / "raw"),
            "--cache-only",
            "--band",
            "00000000-0000-0000-0000-000000000001",
        ]
    )

    assert args.raw_root == tmp_path / "raw"
    assert args.cache_only is True
    assert args.bands == ["00000000-0000-0000-0000-000000000001"]


def test_main_returns_success_code_from_run_ingest(monkeypatch) -> None:
    monkeypatch.setenv("MUSICBRAINZ_USER_AGENT", "HMDE/0.1 (test@example.test)")
    observed = []

    def fake_run(options, settings):
        observed.append(options)
        return 0

    monkeypatch.setattr(cli, "run_ingest", fake_run)

    assert cli.main(["ingest"]) == 0
    assert observed[0].raw_root == cli.DEFAULT_RAW_ROOT


def test_main_returns_partial_code_from_run_ingest(monkeypatch) -> None:
    monkeypatch.setenv("MUSICBRAINZ_USER_AGENT", "HMDE/0.1 (test@example.test)")
    monkeypatch.setattr(cli, "run_ingest", lambda options, settings: 2)

    assert cli.main(["ingest"]) == 2


def test_main_returns_failure_on_unhandled_error(monkeypatch) -> None:
    monkeypatch.setenv("MUSICBRAINZ_USER_AGENT", "HMDE/0.1 (test@example.test)")

    def fail(options, settings):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(cli, "run_ingest", fail)

    assert cli.main(["ingest"]) == 1


def test_main_requires_user_agent_for_live_ingestion(monkeypatch, capsys) -> None:
    monkeypatch.delenv("MUSICBRAINZ_USER_AGENT", raising=False)

    assert cli.main(["ingest"]) == 1
    assert "MUSICBRAINZ_USER_AGENT is required" in capsys.readouterr().err
