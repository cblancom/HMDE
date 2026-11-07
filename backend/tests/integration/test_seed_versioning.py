from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hmde.etl.musicbrainz.seed import load_seed_list

DATA = Path(__file__).resolve().parents[3] / "data"
ARCHIVE = DATA / "seed-lists" / "v0.1.0.json"
POINTER = DATA / "seed-list.json"
BATCH = DATA / "seed-lists" / "batches" / "v0.2.0-batch-01.json"
ARCHIVE_SHA256 = "46028de3834515c0f2d2d71afc371e8d22f67e813df62235e3a776f347c61c43"


def test_v01_archive_is_immutable() -> None:
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA256


def test_pointer_resolves_to_v02_without_duplicating_the_corpus() -> None:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))

    assert pointer == {"active_version": "0.2.0", "path": "seed-lists/v0.2.0.json"}
    assert "bands" not in pointer


def test_v02_is_the_approved_42_plus_15_composition() -> None:
    old = load_seed_list(ARCHIVE)
    current = load_seed_list(POINTER)
    batch = json.loads(BATCH.read_text(encoding="utf-8"))

    old_mbids = {band.mbid for band in old.bands}
    current_mbids = {band.mbid for band in current.bands}
    batch_mbids = {band["mbid"] for band in batch["bands"]}

    assert len(current.bands) == 57
    assert len(current.active_bands) == 57
    assert old_mbids <= current_mbids
    assert current_mbids - old_mbids == batch_mbids
    assert len(batch_mbids) == 15
    assert all(band.lifecycle == "active" for band in current.bands)
