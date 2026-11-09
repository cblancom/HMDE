from __future__ import annotations

from dataclasses import replace

import pandas as pd

from hmde.analytics.metrics import producer_metrics
from tests.unit.test_analysis_distributions import _frames


def _producer_frames():
    credits = pd.DataFrame(
        [
            {
                "artist_id": "p1",
                "artist_name": "Producer One",
                "role_code": "producer",
                "release_group_id": "a1",
                "scope": "release",
            },
            {
                "artist_id": "p1",
                "artist_name": "Producer One",
                "role_code": "co-producer",
                "release_group_id": "a2",
                "scope": "release",
            },
            {
                "artist_id": "p2",
                "artist_name": "Producer Two",
                "role_code": "producer",
                "release_group_id": "a1",
                "scope": "release",
            },
            {
                "artist_id": "p3",
                "artist_name": "Engineer One",
                "role_code": "engineer",
                "release_group_id": "a2",
                "scope": "recording",
            },
        ]
    )
    return replace(_frames(), credits=credits)


def test_producer_metrics_isolate_production_roles() -> None:
    metrics = producer_metrics(_producer_frames())
    by_key = {(m.metric_code, m.scope_key): m for m in metrics}

    assert by_key[("EDA-PROD-001", "Producer One")].numerator == 2
    assert ("EDA-PROD-001", "Engineer One") not in by_key
    assert by_key[("EDA-CONC-001", "top10")].details["k"] == 10
    assert 0 <= by_key[("EDA-CONC-002", "hhi")].value <= 1
    assert by_key[("EDA-CONC-003", "to_50_percent")].value >= 1
