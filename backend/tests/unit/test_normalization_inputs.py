from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from hmde.normalization.errors import InputValidationError
from hmde.normalization.inputs import validate_inputs

DATA = Path(__file__).resolve().parents[3] / "data"
MINI_DATASET = Path(__file__).resolve().parents[1] / "fixtures" / "normalization" / "mini-dataset"
TAXONOMY = DATA / "taxonomy.json"
TAG_MAP = DATA / "classifications" / "tag-map-v0.1.0.json"
OVERRIDES = DATA / "classifications" / "manual-overrides-v0.1.0.json"


def _validate(dataset: Path = MINI_DATASET, **overrides):
    values = {
        "taxonomy_path": TAXONOMY,
        "tag_map_path": TAG_MAP,
        "overrides_path": OVERRIDES,
    }
    values.update(overrides)
    return validate_inputs(dataset, **values)


def test_validate_inputs_reads_manifest_files_and_versions() -> None:
    inputs = _validate()

    assert inputs.dataset.dataset_version == "mini-20261108"
    assert inputs.dataset.seed_list_version == "0.2.0"
    assert inputs.dataset.taxonomy_version == "0.2.0"
    assert inputs.dataset.band_count == 1
    assert inputs.dataset.file("artists.ndjson").count == 1
    assert inputs.dataset.batch_ids == ("v0.1.0",)
    assert inputs.taxonomy.version == "0.2.0"
    assert len(inputs.tag_map.rules) == 48
    assert len(inputs.overrides.overrides) == 13


def test_validate_inputs_rejects_checksum_mismatch(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    shutil.copytree(MINI_DATASET, dataset)
    artists = dataset / "artists.ndjson"
    artists.write_text(artists.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(InputValidationError, match="checksum"):
        _validate(dataset)


def test_validate_inputs_rejects_wrong_seed_list_version(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    shutil.copytree(MINI_DATASET, dataset)
    manifest_path = dataset / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["seed_list_version"] = "0.1.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(InputValidationError, match="seed-list version"):
        _validate(dataset)


def test_validate_inputs_rejects_tag_map_parent(tmp_path: Path) -> None:
    tag_map = json.loads(TAG_MAP.read_text(encoding="utf-8"))
    tag_map["rules"][0]["target_code"] = "metal"
    path = tmp_path / "tag-map.json"
    path.write_text(json.dumps(tag_map), encoding="utf-8")

    with pytest.raises(InputValidationError, match="assignable taxonomy leaf"):
        _validate(tag_map_path=path)


def test_validate_inputs_rejects_invalid_override(tmp_path: Path) -> None:
    overrides = {
        "schema_version": 1,
        "version": "0.1.0",
        "taxonomy_version": "0.2.0",
        "overrides": [
            {
                "release_group_mbid": "22222222-2222-4222-8222-222222222222",
                "primary_code": "metal",
                "secondary_codes": [],
                "confidence": 1.0,
                "reason": "test",
                "reviewer": "tester",
                "reviewed_at": "2026-11-08",
            }
        ],
    }
    path = tmp_path / "overrides.json"
    path.write_text(json.dumps(overrides), encoding="utf-8")

    with pytest.raises(InputValidationError, match="primary"):
        _validate(overrides_path=path)
