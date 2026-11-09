from __future__ import annotations

from dataclasses import replace

import pandas as pd

from hmde.analytics.metrics import coverage_metrics, limitation_metrics
from tests.unit.test_analysis_distributions import _frames


def test_coverage_metrics_include_unknown_and_sources() -> None:
    metrics = coverage_metrics(_frames())
    by_key = {(m.metric_code, m.scope_type, m.scope_key): m for m in metrics}

    assert by_key[("EDA-COV-001", "country", "GB")].numerator == 1
    assert by_key[("EDA-COV-001", "country", "US")].numerator == 1
    assert by_key[("EDA-COV-002", "batch", "v0.1.0")].numerator == 2
    assert by_key[("EDA-COV-003", "source", "musicbrainz")].numerator == 3


def test_limitation_metrics_expose_missing_data() -> None:
    frames = _frames()
    frames = replace(
        frames,
        quality=pd.DataFrame(
            [
                {
                    "rule_code": "Q-CLS-001",
                    "severity": "blocking",
                    "status": "exceptional",
                    "count": 2,
                }
            ]
        ),
        active_exceptions=2,
    )
    metrics = limitation_metrics(frames)
    by_key = {(m.metric_code, m.scope_type, m.scope_key): m for m in metrics}

    assert by_key[("EDA-LIM-001", "quality", "findings")].numerator == 2
    assert by_key[("EDA-LIM-002", "field", "album_date")].numerator == 1
    assert by_key[("EDA-LIM-002", "field", "band_wikidata_qid")].numerator == 1
