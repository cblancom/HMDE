from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.quality.catalogue import load_rule_catalogue
from hmde.quality.errors import QualityCatalogueError

CATALOGUE = Path(__file__).resolve().parents[3] / "data" / "quality" / "rules-v0.1.0.json"


def test_load_catalogue_reads_versioned_rules() -> None:
    catalogue = load_rule_catalogue(CATALOGUE)

    assert catalogue.version == "0.1.0"
    assert catalogue.schema_version == 1
    assert len(catalogue.rules) == 20
    assert len(catalogue.by_code()) == 20
    assert catalogue.by_code()["Q-PROV-001"].severity == "blocking"


def test_load_catalogue_rejects_duplicate_rule_codes(tmp_path: Path) -> None:
    payload = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    payload["rules"][1]["code"] = payload["rules"][0]["code"]
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QualityCatalogueError, match="duplicate"):
        load_rule_catalogue(path)


def test_load_catalogue_rejects_invalid_dimension(tmp_path: Path) -> None:
    payload = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    payload["rules"][0]["dimension"] = "made-up"
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QualityCatalogueError, match="dimension"):
        load_rule_catalogue(path)


def test_load_catalogue_rejects_invalid_severity(tmp_path: Path) -> None:
    payload = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    payload["rules"][0]["severity"] = "critical"
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QualityCatalogueError, match="severity"):
        load_rule_catalogue(path)
