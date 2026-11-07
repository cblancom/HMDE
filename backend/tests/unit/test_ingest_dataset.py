from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from hmde.etl.musicbrainz.dataset import (
    ARTISTS_FILE,
    CREDITS_FILE,
    EXCLUSIONS_FILE,
    MANIFEST_FILE,
    RELEASE_GROUPS_FILE,
    write_dataset,
)
from tests.support.extractions import sample_extraction

SOURCE_TIME = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def test_write_dataset_creates_files_and_manifest(tmp_path: Path) -> None:
    result = write_dataset(
        [sample_extraction()],
        tmp_path,
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    assert result.path == tmp_path / result.dataset_version
    assert result.path.is_dir()
    for name in (
        ARTISTS_FILE,
        RELEASE_GROUPS_FILE,
        CREDITS_FILE,
        EXCLUSIONS_FILE,
    ):
        assert (result.path / name).is_file()
    manifest = json.loads((result.path / MANIFEST_FILE).read_text(encoding="utf-8"))
    assert manifest == result.manifest
    assert manifest["dataset_version"] == result.dataset_version
    assert manifest["seed_list_version"] == "0.1.0"
    assert manifest["band_count"] == 1
    assert manifest["files"]["artists.ndjson"]["count"] == 1
    assert manifest["files"]["credits.ndjson"]["count"] == 3
    assert manifest["files"]["exclusions.ndjson"]["count"] == 1


def test_dataset_records_keep_raw_response_ids(tmp_path: Path) -> None:
    result = write_dataset(
        [sample_extraction()],
        tmp_path,
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    for name in result.manifest["files"]:
        records = [
            json.loads(line)
            for line in (result.path / name).read_text(encoding="utf-8").splitlines()
        ]
        assert records
        assert all(record["raw_response_id"] for record in records)


def test_dataset_is_deterministic_across_output_roots(tmp_path: Path) -> None:
    first = write_dataset(
        [sample_extraction()],
        tmp_path / "one",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )
    second = write_dataset(
        [sample_extraction()],
        tmp_path / "two",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    assert first.dataset_version == second.dataset_version
    assert first.manifest == second.manifest
    for name in first.manifest["files"]:
        assert (first.path / name).read_bytes() == (second.path / name).read_bytes()


def test_writing_identical_dataset_twice_is_idempotent(tmp_path: Path) -> None:
    first = write_dataset(
        [sample_extraction()],
        tmp_path,
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )
    second = write_dataset(
        [sample_extraction()],
        tmp_path,
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    assert first.dataset_version == second.dataset_version
    assert first.path == second.path


def test_dataset_ordering_is_stable_for_records_with_equal_sort_keys(tmp_path: Path) -> None:
    base = sample_extraction()
    first = base.exclusions[0]
    second = replace(first, raw_response_id=uuid.uuid4())
    one = replace(base, exclusions=(first, second))
    two = replace(base, exclusions=(second, first))

    first_result = write_dataset(
        [one],
        tmp_path / "one",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )
    second_result = write_dataset(
        [two],
        tmp_path / "two",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    assert first_result.dataset_version == second_result.dataset_version
    assert (first_result.path / EXCLUSIONS_FILE).read_bytes() == (
        second_result.path / EXCLUSIONS_FILE
    ).read_bytes()
