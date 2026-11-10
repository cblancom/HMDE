from __future__ import annotations


def test_search_returns_grouped_bounded_results(api_client) -> None:
    response = api_client.get("/api/v1/search", params={"q": "iron", "limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "iron"
    assert any(item["name"] == "Iron Maiden" for item in body["bands"])
    assert any("Iron" in item["title"] for item in body["albums"])
    assert len(body["bands"]) <= 5
    assert len(body["albums"]) <= 5
    assert len(body["producers"]) <= 5


def test_search_requires_query(api_client) -> None:
    response = api_client.get("/api/v1/search")
    assert response.status_code == 422
