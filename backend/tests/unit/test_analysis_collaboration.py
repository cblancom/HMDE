from __future__ import annotations

from dataclasses import replace

import pandas as pd

from hmde.analytics.metrics import collaboration_metrics
from tests.unit.test_analysis_distributions import _frames


def test_collaboration_pairs_require_two_shared_albums() -> None:
    credits = pd.DataFrame(
        [
            {
                "artist_id": "p1",
                "artist_name": "One",
                "release_group_id": "a1",
                "role_code": "producer",
                "scope": "release",
            },
            {
                "artist_id": "p2",
                "artist_name": "Two",
                "release_group_id": "a1",
                "role_code": "producer",
                "scope": "release",
            },
            {
                "artist_id": "p1",
                "artist_name": "One",
                "release_group_id": "a2",
                "role_code": "producer",
                "scope": "release",
            },
            {
                "artist_id": "p2",
                "artist_name": "Two",
                "release_group_id": "a2",
                "role_code": "producer",
                "scope": "release",
            },
            {
                "artist_id": "p3",
                "artist_name": "Three",
                "release_group_id": "a1",
                "role_code": "producer",
                "scope": "release",
            },
        ]
    )
    metrics = collaboration_metrics(replace(_frames(), credits=credits))

    assert len(metrics) == 1
    assert metrics[0].scope_key == "One | Two"
    assert metrics[0].numerator == 2
    assert "not influence" in metrics[0].details["warning"]
