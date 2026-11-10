from __future__ import annotations

from hmde.openapi import build_openapi


def test_openapi_includes_catalog_paths() -> None:
    schema = build_openapi()

    assert "/health" in schema["paths"]
    assert "/api/v1/bands" in schema["paths"]
    assert "/api/v1/bands/{band_id}" in schema["paths"]
    assert "/api/v1/bands/{band_id}/graph" in schema["paths"]
    assert "/api/v1/artists/{artist_id}" in schema["paths"]
    assert "/api/v1/albums" in schema["paths"]
    assert "/api/v1/credits" in schema["paths"]
    assert "/api/v1/producers" in schema["paths"]
    assert "/api/v1/producers/{producer_id}/graph" in schema["paths"]
    assert "/api/v1/analysis-runs" in schema["paths"]
    assert "/api/v1/analytics/summary" in schema["paths"]
    assert "/api/v1/communities" in schema["paths"]
    assert "/api/v1/search" in schema["paths"]
    assert "/api/v1/taxonomy" in schema["paths"]


def test_openapi_includes_generated_response_schemas() -> None:
    schema = build_openapi()
    schemas = schema["components"]["schemas"]

    assert "BandListResponse" in schemas
    assert "BandDetailResponse" in schemas
    assert "BandGraphResponse" in schemas
    assert "ProducerGraphResponse" in schemas
    assert "AnalyticsSummaryResponse" in schemas
    assert "TaxonomyResponse" in schemas
    assert "AlbumDetailResponse" in schemas


def test_openapi_exposes_read_only_operations_only() -> None:
    schema = build_openapi()

    for operations in schema["paths"].values():
        assert set(operations) <= {"get"}
