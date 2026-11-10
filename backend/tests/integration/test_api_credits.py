from __future__ import annotations


def test_credit_list_filters(api_client) -> None:
    band = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"}).json()["items"][0]
    album = api_client.get("/api/v1/albums", params={"band_id": band["id"]}).json()["items"][0]

    response = api_client.get(
        "/api/v1/credits",
        params={"album_id": album["id"], "role": "producer", "limit": 200},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(item["album_id"] == album["id"] for item in body["items"])
    assert all(item["role"] == "producer" for item in body["items"])

    invalid = api_client.get("/api/v1/credits", params={"scope": "invalid"})
    assert invalid.status_code == 422
