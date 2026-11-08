from __future__ import annotations

from hmde.normalization.credits import normalize_role


def test_normalize_role_maps_producer_attributes() -> None:
    assert normalize_role("producer", []) == "producer"
    assert normalize_role("producer", ["co"]) == "co-producer"
    assert normalize_role("producer", ["executive"]) == "executive-producer"
    assert normalize_role("producer", ["assistant"]) == "assistant-producer"
    assert normalize_role("producer", ["additional"]) == "additional-producer"
    assert normalize_role("engineer", ["assistant"]) == "engineer"
    assert normalize_role("mix", ["co"]) == "mix"
    assert normalize_role("mastering", []) == "mastering"


def test_normalize_role_rejects_unknown_role() -> None:
    assert normalize_role("guitar", []) is None
