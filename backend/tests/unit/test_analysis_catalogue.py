from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.analytics.catalogue import load_metric_catalogue
from hmde.analytics.errors import MetricCatalogueError

CATALOGUE = Path(__file__).resolve().parents[3] / "data" / "metrics" / "catalogue-v0.1.0.json"


def test_load_metric_catalogue() -> None:
    catalogue = load_metric_catalogue(CATALOGUE)

    assert catalogue.version == "0.1.0"
    assert len(catalogue.metrics) == 20
    assert len(catalogue.by_code()) == 20
    assert "EDA-CONC-002" in catalogue.by_code()


def test_duplicate_metric_codes_rejected(tmp_path: Path) -> None:
    payload = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    payload["metrics"][1]["code"] = payload["metrics"][0]["code"]
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(MetricCatalogueError, match="duplicate"):
        load_metric_catalogue(path)


def test_missing_definition_fields_rejected(tmp_path: Path) -> None:
    payload = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    payload["metrics"][0]["numerator"] = ""
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(MetricCatalogueError, match="missing fields"):
        load_metric_catalogue(path)
