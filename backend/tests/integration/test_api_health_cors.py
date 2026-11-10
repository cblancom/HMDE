from __future__ import annotations


def test_health_and_cors_allow_configured_origin(api_client) -> None:
    response = api_client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_does_not_reflect_unknown_origin(api_client) -> None:
    response = api_client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
