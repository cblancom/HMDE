from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.network.errors import NetworkInputError
from hmde.network.inputs import _taxonomy_version


def test_taxonomy_version_reads_version(tmp_path: Path) -> None:
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps({"version": "0.2.0"}), encoding="utf-8")
    assert _taxonomy_version(path) == "0.2.0"


def test_taxonomy_version_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "taxonomy.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(NetworkInputError, match="could not read taxonomy"):
        _taxonomy_version(path)


def test_taxonomy_version_rejects_missing_version(tmp_path: Path) -> None:
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
    with pytest.raises(NetworkInputError, match="missing a valid version"):
        _taxonomy_version(path)
