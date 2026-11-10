from __future__ import annotations


def test_band_decade_filter_and_limit(api_client) -> None:
    response = api_client.get(
        "/api/v1/bands",
        params={"q": "Iron Maiden", "decade": "1980s", "limit": 200},
    )
    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["items"]] == ["Iron Maiden"]


def test_band_invalid_decade_returns_422(api_client) -> None:
    response = api_client.get("/api/v1/bands", params={"decade": "1980"})
    assert response.status_code == 422
