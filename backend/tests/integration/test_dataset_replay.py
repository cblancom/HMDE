from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from hmde.etl.musicbrainz.dataset import MANIFEST_FILE, write_dataset
from tests.support.extractions import sample_extraction

SOURCE_TIME = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def test_offline_replay_produces_the_same_manifest(tmp_path: Path) -> None:
    original = write_dataset(
        [sample_extraction()],
        tmp_path / "original",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )
    replay = write_dataset(
        [sample_extraction()],
        tmp_path / "replay",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
    )

    original_manifest = json.loads((original.path / MANIFEST_FILE).read_text(encoding="utf-8"))
    replay_manifest = json.loads((replay.path / MANIFEST_FILE).read_text(encoding="utf-8"))

    assert original.dataset_version == replay.dataset_version
    assert original_manifest == replay_manifest
