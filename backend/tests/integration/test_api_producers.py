from __future__ import annotations


def test_producer_list_detail_and_unknown(api_client, network_analysis_run) -> None:
    response = api_client.get(
        "/api/v1/producers",
        params={"limit": 200, "sort": "album_count", "order": "desc"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    producer = next(item for item in body["items"] if item["band_count"] > 0)

    detail = api_client.get(f"/api/v1/producers/{producer['id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["id"] == producer["id"]
    assert detail_body["top_albums"]
    assert detail_body["meta"]["analysis_run_id"] == str(network_analysis_run)

    missing = api_client.get("/api/v1/producers/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Producer not found"
