from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.normalization.errors import TaxonomyValidationError
from hmde.normalization.taxonomy import (
    load_taxonomy_document,
    parse_taxonomy_payload,
)

TAXONOMY_PATH = Path(__file__).resolve().parents[3] / "data" / "taxonomy.json"


def _payload() -> dict:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def test_load_taxonomy_document_reads_approved_tree() -> None:
    document = load_taxonomy_document(TAXONOMY_PATH)

    assert document.version == "0.2.0"
    assert len(document.entries) == 23
    assert document.assignable_leaves == frozenset(
        entry.code for entry in document.entries if entry.assignable
    )
    assert document.by_code["heavy-metal"].parent_code == "traditional-metal"
    assert document.by_code["metal"].parent_code is None


def test_parse_taxonomy_rejects_duplicate_codes() -> None:
    payload = _payload()
    payload["nodes"][1]["code"] = payload["nodes"][0]["code"]

    with pytest.raises(TaxonomyValidationError, match="duplicate"):
        parse_taxonomy_payload(payload)


def test_parse_taxonomy_rejects_missing_parent() -> None:
    payload = _payload()
    payload["nodes"][1]["parent_code"] = "missing"

    with pytest.raises(TaxonomyValidationError, match="unknown parent"):
        parse_taxonomy_payload(payload)


def test_parse_taxonomy_rejects_cycle() -> None:
    payload = _payload()
    payload["nodes"][0]["parent_code"] = "traditional-metal"

    with pytest.raises(TaxonomyValidationError, match="cycle"):
        parse_taxonomy_payload(payload)


def test_parse_taxonomy_rejects_assignable_parent() -> None:
    payload = _payload()
    payload["nodes"][1]["assignable"] = True

    with pytest.raises(TaxonomyValidationError, match="assignable but has children"):
        parse_taxonomy_payload(payload)


def test_parse_taxonomy_rejects_non_assignable_leaf() -> None:
    payload = _payload()
    payload["nodes"][2]["assignable"] = False

    with pytest.raises(TaxonomyValidationError, match="must be assignable"):
        parse_taxonomy_payload(payload)
