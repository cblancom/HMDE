from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.etl.musicbrainz.seed import SeedListError, load_seed_list, select_bands

DATA = Path(__file__).resolve().parents[3] / "data"
TAXONOMY_PATH = DATA / "taxonomy.json"
V02_PATH = DATA / "seed-lists" / "v0.2.0.json"
POINTER_PATH = DATA / "seed-list.json"


def _payload() -> dict:
    return json.loads(V02_PATH.read_text(encoding="utf-8"))


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "seed-lists" / "v0.2.0.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _load_payload(tmp_path: Path, payload: dict):
    return load_seed_list(_write_payload(tmp_path, payload), taxonomy_path=TAXONOMY_PATH)


def test_active_pointer_loads_v02_corpus() -> None:
    seed_list = load_seed_list(POINTER_PATH)

    assert seed_list.version == "0.2.0"
    assert seed_list.schema_version == 2
    assert seed_list.taxonomy_version == "0.2.0"
    assert seed_list.period_start.isoformat() == "1960-01-01"
    assert seed_list.period_end.isoformat() == "2026-12-31"
    assert len(seed_list.bands) == 57
    assert len(seed_list.active_bands) == 57
    assert {batch.batch_id for batch in seed_list.batches} == {
        "v0.1.0",
        "v0.2.0-batch-01",
    }
    assert all(band.subgenre for band in seed_list.bands)
    assert all(band.seed_subgenre_code for band in seed_list.bands)


def test_v01_archive_remains_loadable() -> None:
    seed_list = load_seed_list(DATA / "seed-lists" / "v0.1.0.json")

    assert seed_list.version == "0.1.0"
    assert seed_list.schema_version == 1
    assert len(seed_list.bands) == 42


def test_pointer_rejects_version_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "seed-lists" / "target.json"
    target.parent.mkdir()
    target.write_text(json.dumps({"version": "0.2.0", "bands": []}), encoding="utf-8")
    pointer = tmp_path / "seed-list.json"
    pointer.write_text(
        json.dumps({"active_version": "9.9.9", "path": "seed-lists/target.json"}),
        encoding="utf-8",
    )

    with pytest.raises(SeedListError, match="version mismatch"):
        load_seed_list(pointer)


def test_pointer_rejects_path_escape(tmp_path: Path) -> None:
    pointer = tmp_path / "seed-list.json"
    pointer.write_text(
        json.dumps({"active_version": "0.2.0", "path": "../outside.json"}),
        encoding="utf-8",
    )

    with pytest.raises(SeedListError, match="escapes"):
        load_seed_list(pointer)


def test_taxonomy_parent_node_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["seed_subgenre_code"] = "metal"

    with pytest.raises(SeedListError, match="assignable taxonomy leaf"):
        _load_payload(tmp_path, payload)


def test_unknown_taxonomy_code_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["seed_subgenre_code"] = "unknown-metal"

    with pytest.raises(SeedListError, match="assignable taxonomy leaf"):
        _load_payload(tmp_path, payload)


def test_retired_band_is_excluded_from_default_selection(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["lifecycle"] = "retired"
    seed_list = _load_payload(tmp_path, payload)
    retired = seed_list.bands[0]

    assert len(seed_list.active_bands) == 56
    assert all(band.mbid != retired.mbid for band in select_bands(seed_list, (), None))
    with pytest.raises(SeedListError, match="not in the seed list"):
        select_bands(seed_list, (retired.mbid,), None)


def test_invalid_lifecycle_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["lifecycle"] = "deleted"

    with pytest.raises(SeedListError, match="invalid lifecycle"):
        _load_payload(tmp_path, payload)


def test_unverified_band_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["status"] = "pending"

    with pytest.raises(SeedListError, match="not verified"):
        _load_payload(tmp_path, payload)


def test_duplicate_mbid_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][1]["mbid"] = payload["bands"][0]["mbid"]

    with pytest.raises(SeedListError, match="duplicate"):
        _load_payload(tmp_path, payload)


def test_duplicate_sequence_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][1]["sequence"] = payload["bands"][0]["sequence"]

    with pytest.raises(SeedListError, match="duplicate seed-list sequence"):
        _load_payload(tmp_path, payload)


def test_unknown_batch_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["batch_id"] = "missing-batch"

    with pytest.raises(SeedListError, match="unknown batch"):
        _load_payload(tmp_path, payload)


def test_batch_count_mismatch_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["batches"][0]["band_count"] = 41

    with pytest.raises(SeedListError, match="batch counts"):
        _load_payload(tmp_path, payload)


def test_distribution_mismatch_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["subgenre_distribution"]["heavy-metal"] += 1

    with pytest.raises(SeedListError, match="subgenre_distribution"):
        _load_payload(tmp_path, payload)


def test_total_band_count_mismatch_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["total_bands"] = 58

    with pytest.raises(SeedListError, match="total_bands"):
        _load_payload(tmp_path, payload)


def test_taxonomy_version_mismatch_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["taxonomy_version"] = "0.1.0"

    with pytest.raises(SeedListError, match="taxonomy version mismatch"):
        _load_payload(tmp_path, payload)


def test_invalid_period_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["period_start"] = "2027-01-01"

    with pytest.raises(SeedListError, match="period_start"):
        _load_payload(tmp_path, payload)


def test_self_replacement_is_rejected(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["replaced_by_mbid"] = payload["bands"][0]["mbid"]

    with pytest.raises(SeedListError, match="replace itself"):
        _load_payload(tmp_path, payload)
