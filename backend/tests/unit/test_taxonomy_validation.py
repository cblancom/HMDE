from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.etl.musicbrainz.seed import TaxonomyError, load_taxonomy

TAXONOMY_PATH = Path(__file__).resolve().parents[3] / "data" / "taxonomy.json"


def _payload() -> dict:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_taxonomy_reads_approved_tree() -> None:
    taxonomy = load_taxonomy(TAXONOMY_PATH)

    assert taxonomy.version == "0.2.0"
    assert len(taxonomy.nodes) == 23
    assert sum(node.assignable for node in taxonomy.nodes) == 17
    assert taxonomy.is_assignable("heavy-metal")
    assert taxonomy.is_assignable("post-metal")
    assert not taxonomy.is_assignable("metal")
    assert not taxonomy.is_assignable("unknown")


def test_load_taxonomy_rejects_duplicate_codes(tmp_path: Path) -> None:
    payload = _payload()
    payload["nodes"][1]["code"] = payload["nodes"][0]["code"]

    with pytest.raises(TaxonomyError, match="duplicate"):
        load_taxonomy(_write_payload(tmp_path, payload))


def test_load_taxonomy_rejects_missing_parent(tmp_path: Path) -> None:
    payload = _payload()
    payload["nodes"][1]["parent_code"] = "missing-parent"

    with pytest.raises(TaxonomyError, match="unknown parent"):
        load_taxonomy(_write_payload(tmp_path, payload))


def test_load_taxonomy_rejects_cycles(tmp_path: Path) -> None:
    payload = _payload()
    payload["nodes"][0]["parent_code"] = "traditional-metal"

    with pytest.raises(TaxonomyError, match="cycle"):
        load_taxonomy(_write_payload(tmp_path, payload))


def test_load_taxonomy_rejects_assignable_parent(tmp_path: Path) -> None:
    payload = _payload()
    payload["nodes"][1]["assignable"] = True

    with pytest.raises(TaxonomyError, match="assignable but has children"):
        load_taxonomy(_write_payload(tmp_path, payload))


def test_load_taxonomy_rejects_non_assignable_leaf(tmp_path: Path) -> None:
    payload = _payload()
    payload["nodes"][2]["assignable"] = False

    with pytest.raises(TaxonomyError, match="must be assignable"):
        load_taxonomy(_write_payload(tmp_path, payload))
