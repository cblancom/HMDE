from __future__ import annotations

import pandas as pd

from hmde.analytics.loader import AnalysisFrames
from hmde.analytics.metrics import distribution_metrics


def _frames() -> AnalysisFrames:
    bands = pd.DataFrame(
        [
            {
                "id": "b1",
                "mbid": "1",
                "name": "Band One",
                "country": "GB",
                "aggregate_code": "heavy-metal",
                "aggregate_status": "accepted",
                "qid": "Q1",
            },
            {
                "id": "b2",
                "mbid": "2",
                "name": "Band Two",
                "country": "US",
                "aggregate_code": "thrash-metal",
                "aggregate_status": "accepted",
                "qid": None,
            },
        ]
    )
    albums = pd.DataFrame(
        [
            {
                "id": "a1",
                "first_release_date": "1969-01-01",
                "first_release_precision": "day",
                "primary_code": "heavy-metal",
                "artist_country": "GB",
            },
            {
                "id": "a2",
                "first_release_date": "2000-01-01",
                "first_release_precision": "year",
                "primary_code": "thrash-metal",
                "artist_country": "US",
            },
            {
                "id": "a3",
                "first_release_date": None,
                "first_release_precision": "unknown",
                "primary_code": None,
                "artist_country": None,
            },
        ]
    )
    secondary = pd.DataFrame(
        [{"release_group_id": "a1", "subgenre_code": "hard-rock", "status": "accepted"}]
    )
    credits = pd.DataFrame(
        [
            {"artist_id": "p1", "role_code": "producer", "scope": "release"},
            {"artist_id": "p2", "role_code": "engineer", "scope": "recording"},
        ]
    )
    membership = pd.DataFrame([{"batch_id": "v0.1.0", "lifecycle": "active", "count": 2}])
    taxonomy = pd.DataFrame(
        [
            {"code": "metal", "name": "Metal", "parent_code": None, "assignable": False},
            {
                "code": "traditional-metal",
                "name": "Traditional Metal",
                "parent_code": "metal",
                "assignable": False,
            },
            {
                "code": "heavy-metal",
                "name": "Heavy Metal",
                "parent_code": "traditional-metal",
                "assignable": True,
            },
            {
                "code": "thrash-metal",
                "name": "Thrash Metal",
                "parent_code": "traditional-metal",
                "assignable": True,
            },
            {
                "code": "hard-rock",
                "name": "Hard Rock",
                "parent_code": "traditional-metal",
                "assignable": True,
            },
        ]
    )
    return AnalysisFrames(
        bands=bands,
        albums=albums,
        secondary_labels=secondary,
        credits=credits,
        membership=membership,
        sources=pd.DataFrame([{"source": "musicbrainz", "count": 3}]),
        quality=pd.DataFrame(),
        taxonomy=taxonomy,
        active_exceptions=0,
        entity_counts={"bands": 2, "albums": 3, "releases": 3, "recordings": 4, "credits": 2},
    )


def test_distribution_metrics_are_denominator_aware() -> None:
    metrics = distribution_metrics(_frames())
    by_key = {(m.metric_code, m.scope_type, m.scope_key): m for m in metrics}

    assert by_key[("EDA-TIME-001", "decade", "1960s")].numerator == 1
    assert by_key[("EDA-TIME-001", "decade", "2000s")].numerator == 1
    assert by_key[("EDA-TIME-001", "decade", "unknown")].numerator == 1
    assert by_key[("EDA-TAX-001", "leaf", "heavy-metal")].denominator == 2
    assert by_key[("EDA-TAX-004", "family", "traditional-metal")].numerator == 2
    assert by_key[("EDA-TAX-002", "leaf", "thrash-metal")].numerator == 1
    assert by_key[("EDA-ROLE-001", "role", "producer")].value == 0.5
    assert by_key[("EDA-ROLE-002", "scope", "recording")].value == 0.5
