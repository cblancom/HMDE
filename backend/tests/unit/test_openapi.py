from __future__ import annotations

from hmde.openapi import build_openapi


def test_openapi_includes_catalog_paths() -> None:
    schema = build_openapi()

    assert "/health" in schema["paths"]
    assert "/api/v1/bands" in schema["paths"]
    assert "/api/v1/bands/{band_id}" in schema["paths"]
    assert "/api/v1/bands/{band_id}/graph" in schema["paths"]


def test_openapi_includes_generated_response_schemas() -> None:
    schema = build_openapi()
    schemas = schema["components"]["schemas"]

    assert "BandListResponse" in schemas
    assert "BandDetailResponse" in schemas
    assert "BandGraphResponse" in schemas


def test_openapi_exposes_read_only_operations_only() -> None:
    schema = build_openapi()

    for operations in schema["paths"].values():
        assert set(operations) <= {"get"}
