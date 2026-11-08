from __future__ import annotations

from pathlib import Path

from hmde.normalization import cli


def test_parser_defaults() -> None:
    args = cli.build_parser().parse_args(["run"])

    assert args.dataset == cli.DEFAULT_DATASET
    assert args.taxonomy == cli.DEFAULT_TAXONOMY
    assert args.tag_map == cli.DEFAULT_TAG_MAP
    assert args.overrides == cli.DEFAULT_OVERRIDES
    assert args.seed_list == cli.DEFAULT_SEED_LIST
    assert args.output == cli.DEFAULT_OUTPUT
    assert args.dry_run is False


def test_parser_accepts_explicit_paths(tmp_path: Path) -> None:
    args = cli.build_parser().parse_args(
        [
            "run",
            "--dataset",
            str(tmp_path / "dataset"),
            "--output",
            str(tmp_path / "output"),
            "--dry-run",
        ]
    )

    assert args.dataset == tmp_path / "dataset"
    assert args.output == tmp_path / "output"
    assert args.dry_run is True


def test_main_returns_cli_exit_codes(monkeypatch) -> None:
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 0)
    assert cli.main(["run"]) == 0
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 2)
    assert cli.main(["run"]) == 2
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 1)
    assert cli.main(["run"]) == 1
