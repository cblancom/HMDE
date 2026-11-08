from __future__ import annotations

from collections import Counter

from hmde.normalization.aggregates import choose_aggregate


def test_accepted_majority() -> None:
    decision = choose_aggregate(
        Counter({"heavy-metal": 4, "thrash-metal": 1}),
        seed_code="heavy-metal",
    )

    assert decision.code == "heavy-metal"
    assert decision.status == "accepted"
    assert decision.confidence == 0.8
    assert decision.issue_type is None


def test_review_majority() -> None:
    decision = choose_aggregate(
        Counter({"heavy-metal": 3, "thrash-metal": 1}),
        seed_code="heavy-metal",
    )

    assert decision.status == "review"
    assert decision.issue_type == "aggregate_review"


def test_tie_uses_seed_leaf() -> None:
    decision = choose_aggregate(
        Counter({"heavy-metal": 2, "thrash-metal": 2}),
        seed_code="thrash-metal",
    )

    assert decision.code == "thrash-metal"
    assert decision.status == "review"
    assert decision.mapping_rule == "seed-tiebreak"
    assert decision.issue_type == "aggregate_tie"


def test_low_confidence_uses_seed_leaf_for_review() -> None:
    decision = choose_aggregate(
        Counter({"heavy-metal": 3, "nwobhm": 2, "progressive-metal": 2}),
        seed_code="heavy-metal",
    )

    assert decision.code == "heavy-metal"
    assert decision.status == "review"
    assert decision.mapping_rule == "seed-low-confidence"
    assert decision.issue_type == "aggregate_low_confidence"


def test_empty_counts_use_seed_fallback() -> None:
    decision = choose_aggregate(Counter(), seed_code="doom-metal")

    assert decision.code == "doom-metal"
    assert decision.status == "review"
    assert decision.mapping_rule == "seed-fallback"


def test_empty_counts_without_seed_are_missing() -> None:
    decision = choose_aggregate(Counter(), seed_code=None)

    assert decision.code is None
    assert decision.status == "quarantined"
    assert decision.issue_type == "aggregate_missing"
