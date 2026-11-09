from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.quality.catalogue import load_rule_catalogue
from hmde.quality.errors import QualityInputError
from hmde.quality.exceptions import load_exception_baseline

DATA = Path(__file__).resolve().parents[3] / "data"
CATALOGUE = DATA / "quality" / "rules-v0.1.0.json"
EXCEPTIONS = DATA / "quality" / "exceptions-v0.1.0.json"


def test_exception_baseline_has_58_approved_entries() -> None:
    catalogue = load_rule_catalogue(CATALOGUE)
    baseline = load_exception_baseline(EXCEPTIONS, catalogue)

    assert baseline.version == "0.1.0"
    assert len(baseline.exceptions) == 58
    assert {item.rule_code for item in baseline.exceptions} == {
        "Q-CLS-001",
        "Q-CLS-002",
        "Q-AGG-001",
    }
    assert all(item.approved_by for item in baseline.exceptions)


def test_exception_baseline_rejects_missing_approver(tmp_path: Path) -> None:
    catalogue = load_rule_catalogue(CATALOGUE)
    payload = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    payload["exceptions"][0]["approved_by"] = ""
    path = tmp_path / "exceptions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(QualityInputError, match="approved_by"):
        load_exception_baseline(path, catalogue)
