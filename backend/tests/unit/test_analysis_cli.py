from __future__ import annotations

from hmde.analytics import cli


def test_parser_requires_runs() -> None:
    args = cli.build_parser().parse_args(
        [
            "run",
            "--normalization-run",
            "00000000-0000-4000-8000-000000000001",
            "--quality-run",
            "00000000-0000-4000-8000-000000000002",
        ]
    )

    assert args.normalization_run is not None
    assert args.quality_run is not None
    assert args.taxonomy == cli.DEFAULT_TAXONOMY
    assert args.catalogue == cli.DEFAULT_CATALOGUE


def test_main_maps_exit_codes(monkeypatch) -> None:
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 0)
    assert (
        cli.main(
            [
                "run",
                "--normalization-run",
                "00000000-0000-4000-8000-000000000001",
                "--quality-run",
                "00000000-0000-4000-8000-000000000002",
            ]
        )
        == 0
    )
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 2)
    assert (
        cli.main(
            [
                "run",
                "--normalization-run",
                "00000000-0000-4000-8000-000000000001",
                "--quality-run",
                "00000000-0000-4000-8000-000000000002",
            ]
        )
        == 2
    )
    monkeypatch.setattr(cli, "run_cli", lambda options, settings: 1)
    assert (
        cli.main(
            [
                "run",
                "--normalization-run",
                "00000000-0000-4000-8000-000000000001",
                "--quality-run",
                "00000000-0000-4000-8000-000000000002",
            ]
        )
        == 1
    )
