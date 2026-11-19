from __future__ import annotations

from pathlib import Path

from hmde.quality.inputs import _active_seed_bands
from hmde.quality.structural import membership_finding

DATA = Path(__file__).resolve().parents[3] / "data"


def test_active_seed_band_counts() -> None:
    assert _active_seed_bands(DATA / "seed-lists" / "v0.2.0.json", expected_version="0.2.0") == 57
    assert _active_seed_bands(DATA / "seed-lists" / "v0.3.0.json", expected_version="0.3.0") == 509


def test_membership_rule_accepts_matching_counts() -> None:
    assert membership_finding(active=57, expected=57, dataset_version="v0.2") is None
    assert membership_finding(active=509, expected=509, dataset_version="v0.3") is None


def test_membership_rule_reports_the_active_seed_count() -> None:
    finding = membership_finding(active=57, expected=509, dataset_version="v0.3")

    assert finding is not None
    assert finding.rule_code == "Q-MEM-001"
    assert finding.observed_value == {"active_memberships": 57}
    assert finding.expected_value == {"active_memberships": 509}
    assert finding.details == {"dataset_version": "v0.3"}
