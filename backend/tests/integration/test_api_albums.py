from __future__ import annotations


def test_album_list_and_filter(api_client) -> None:
    response = api_client.get("/api/v1/albums", params={"limit": 200})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 41
    assert body["limit"] == 200
    assert all(item["band_id"] for item in body["items"])

    band = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"}).json()["items"][0]
    filtered = api_client.get("/api/v1/albums", params={"band_id": band["id"]}).json()
    assert filtered["total"] == 3
    assert {item["band_name"] for item in filtered["items"]} == {"Iron Maiden"}


def test_album_detail_and_unknown(api_client) -> None:
    band = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"}).json()["items"][0]
    album = api_client.get("/api/v1/albums", params={"band_id": band["id"]}).json()["items"][0]
    response = api_client.get(f"/api/v1/albums/{album['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == album["id"]
    assert body["band_name"] == "Iron Maiden"
    assert body["credits"]
    assert any(credit["role"] in {"producer", "co-producer"} for credit in body["credits"])
    assert all(
        credit["support_ratio"] is None or 0 <= credit["support_ratio"] <= 1
        for credit in body["credits"]
    )

    missing = api_client.get("/api/v1/albums/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Album not found"
