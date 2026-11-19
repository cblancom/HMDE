from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

from hmde.etl.musicbrainz.dataset import (
    ARTISTS_FILE,
    CREDITS_FILE,
    EXCLUSIONS_FILE,
    MANIFEST_FILE,
    MULTI_ARTIST_RELEASE_GROUP_REASON,
    PLACES_FILE,
    RECORDINGS_FILE,
    RELEASE_GROUPS_FILE,
    RELEASE_RECORDINGS_FILE,
    RELEASES_FILE,
    write_dataset,
)
from tests.support.extractions import RELEASE_GROUP, sample_extraction

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


def test_manifest_records_corpus_and_taxonomy_metadata(tmp_path: Path) -> None:
    result = write_dataset(
        [sample_extraction()],
        tmp_path,
        seed_list_version="0.2.0",
        taxonomy_version="0.2.0",
        period_start=date(1960, 1, 1),
        period_end=date(2026, 12, 31),
        batch_ids=("v0.1.0", "v0.2.0-batch-01"),
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    manifest = result.manifest
    assert manifest["seed_list_version"] == "0.2.0"
    assert manifest["taxonomy_version"] == "0.2.0"
    assert manifest["period_start"] == "1960-01-01"
    assert manifest["period_end"] == "2026-12-31"
    assert manifest["batch_ids"] == ["v0.1.0", "v0.2.0-batch-01"]


def test_metadata_changes_the_dataset_version(tmp_path: Path) -> None:
    first = write_dataset(
        [sample_extraction()],
        tmp_path / "one",
        seed_list_version="0.2.0",
        taxonomy_version="0.2.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )
    second = write_dataset(
        [sample_extraction()],
        tmp_path / "two",
        seed_list_version="0.2.0",
        taxonomy_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    assert first.dataset_version != second.dataset_version


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


def test_recordings_with_equal_mbid_are_canonical_and_deterministic(tmp_path: Path) -> None:
    base = sample_extraction()
    first = base.recordings[0]
    duplicate = replace(first, raw_response_id=uuid.uuid4())
    one = replace(base, recordings=(first, duplicate, base.recordings[1]))
    two = replace(base, recordings=(duplicate, first, base.recordings[1]))

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
    assert (first_result.path / RECORDINGS_FILE).read_bytes() == (
        second_result.path / RECORDINGS_FILE
    ).read_bytes()
    rows = [
        json.loads(line)
        for line in (first_result.path / RECORDINGS_FILE).read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 2
    assert len({row["mbid"] for row in rows}) == 2


def test_multi_artist_release_groups_are_excluded_and_reported(tmp_path: Path) -> None:
    base = sample_extraction()
    other_band = "12121212-1212-4212-8212-121212121212"
    other_artist = replace(base.artist, mbid=other_band, name="Other Band")
    other_group = replace(
        base.release_groups[0],
        artist_mbid=other_band,
        raw_response_id=uuid.uuid4(),
    )
    other = replace(
        base,
        band_mbid=other_band,
        artist=other_artist,
        release_groups=(other_group,),
    )

    result = write_dataset(
        [base, other],
        tmp_path,
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    counts = {name: entry["count"] for name, entry in result.manifest["files"].items()}
    assert result.manifest["band_count"] == 2
    assert counts[ARTISTS_FILE] == 2
    assert counts[RELEASE_GROUPS_FILE] == 0
    assert counts[RELEASES_FILE] == 0
    assert counts[RECORDINGS_FILE] == 0
    assert counts[RELEASE_RECORDINGS_FILE] == 0
    assert counts[CREDITS_FILE] == 0
    assert counts[PLACES_FILE] == 0
    assert counts[EXCLUSIONS_FILE] == 2

    exclusions = [
        json.loads(line)
        for line in (result.path / EXCLUSIONS_FILE).read_text(encoding="utf-8").splitlines()
    ]
    assert {row["reason"] for row in exclusions} == {
        "secondary_type",
        MULTI_ARTIST_RELEASE_GROUP_REASON,
    }
    assert any(
        row["release_group_mbid"] == RELEASE_GROUP
        and row["reason"] == MULTI_ARTIST_RELEASE_GROUP_REASON
        for row in exclusions
    )


def test_multi_artist_exclusion_preserves_a_single_artist_group(tmp_path: Path) -> None:
    base = sample_extraction()
    other_band = "12121212-1212-4212-8212-121212121212"
    other_group = replace(
        base.release_groups[0],
        mbid="13131313-1313-4313-8313-131313131313",
        artist_mbid=other_band,
        raw_response_id=uuid.uuid4(),
    )
    other = replace(
        base,
        band_mbid=other_band,
        artist=replace(base.artist, mbid=other_band, name="Other Band"),
        release_groups=(other_group,),
    )

    result = write_dataset(
        [base, other],
        tmp_path,
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    groups = [
        json.loads(line)
        for line in (result.path / RELEASE_GROUPS_FILE).read_text(encoding="utf-8").splitlines()
    ]
    assert {row["mbid"] for row in groups} == {RELEASE_GROUP, other_group.mbid}
    assert result.manifest["files"][EXCLUSIONS_FILE]["count"] == 1
