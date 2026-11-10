from __future__ import annotations


def test_artist_detail_returns_canonical_artist(api_client) -> None:
    bands = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"}).json()
    band_id = bands["items"][0]["id"]
    response = api_client.get(f"/api/v1/artists/{band_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == band_id
    assert body["name"] == "Iron Maiden"
    assert body["type"] == "group"


def test_artist_detail_unknown_returns_404(api_client) -> None:
    response = api_client.get("/api/v1/artists/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Artist not found"
