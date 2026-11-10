from __future__ import annotations


def test_e7_fixture_supports_full_api_flow(api_client, network_analysis_run) -> None:
    producers = api_client.get("/api/v1/producers", params={"limit": 200, "sort": "album_count"})
    assert producers.status_code == 200
    producer = next(
        item
        for item in producers.json()["items"]
        if item["album_count"] > 1 and item["band_count"] > 0
    )

    detail = api_client.get(f"/api/v1/producers/{producer['id']}")
    assert detail.status_code == 200
    assert detail.json()["top_albums"]
    assert detail.json()["top_bands"]

    albums = api_client.get(
        f"/api/v1/producers/{producer['id']}/graph",
        params={"view": "albums", "limit": 1, "depth": 1},
    )
    assert albums.status_code == 200
    assert albums.json()["meta"]["truncated"] is True
    assert {node["type"] for node in albums.json()["nodes"]} <= {"producer", "album"}

    bands = api_client.get(
        f"/api/v1/producers/{producer['id']}/graph",
        params={"view": "bands", "limit": 100, "depth": 2},
    )
    assert bands.status_code == 200
    assert {node["type"] for node in bands.json()["nodes"]} <= {"producer", "band"}

    summary = api_client.get("/api/v1/analytics/summary")
    assert summary.status_code == 200
    assert summary.json()["meta"]["analysis_run_id"] == str(network_analysis_run)
