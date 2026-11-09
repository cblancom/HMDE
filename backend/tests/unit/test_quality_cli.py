from __future__ import annotations

from pathlib import Path

from hmde.quality import cli


def test_parser_requires_normalization_run() -> None:
    args = cli.build_parser().parse_args(
        ["run", "--normalization-run", "00000000-0000-4000-8000-000000000001"]
    )

    assert args.normalization_run is not None
    assert args.rules == cli.DEFAULT_RULES
    assert args.exceptions == cli.DEFAULT_EXCEPTIONS
    assert args.strict is False


def test_parser_accepts_strict_and_paths(tmp_path: Path) -> None:
    args = cli.build_parser().parse_args(
        [
            "run",
            "--normalization-run",
            "00000000-0000-4000-8000-000000000001",
            "--rules",
            str(tmp_path / "rules.json"),
            "--exceptions",
            str(tmp_path / "exceptions.json"),
            "--output",
            str(tmp_path / "quality"),
            "--strict",
        ]
    )

    assert args.rules == tmp_path / "rules.json"
    assert args.exceptions == tmp_path / "exceptions.json"
    assert args.output == tmp_path / "quality"
    assert args.strict is True


def test_main_maps_quality_status_to_exit_codes(monkeypatch) -> None:
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 0)
    assert cli.main(["run", "--normalization-run", "00000000-0000-4000-8000-000000000001"]) == 0
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 2)
    assert cli.main(["run", "--normalization-run", "00000000-0000-4000-8000-000000000001"]) == 2
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 3)
    assert cli.main(["run", "--normalization-run", "00000000-0000-4000-8000-000000000001"]) == 3
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 1)
    assert cli.main(["run", "--normalization-run", "00000000-0000-4000-8000-000000000001"]) == 1
