from __future__ import annotations


def _producer_id(api_client) -> str:
    body = api_client.get("/api/v1/producers", params={"limit": 200}).json()
    return next(item["id"] for item in body["items"] if item["band_count"] > 0)


def test_producer_album_graph_has_only_producer_and_album_nodes(
    api_client, network_analysis_run
) -> None:
    producer_id = _producer_id(api_client)
    response = api_client.get(
        f"/api/v1/producers/{producer_id}/graph",
        params={"view": "albums", "limit": 5, "include_evidence": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["view"] == "albums"
    assert body["meta"]["analysis_run_id"] == str(network_analysis_run)
    assert body["nodes"]
    assert {node["type"] for node in body["nodes"]} <= {"producer", "album"}
    assert any(edge["layer"] == "producer_album" for edge in body["edges"])


def test_producer_band_graph_has_only_producer_and_band_nodes(
    api_client, network_analysis_run
) -> None:
    producer_id = _producer_id(api_client)
    response = api_client.get(
        f"/api/v1/producers/{producer_id}/graph",
        params={"view": "bands", "limit": 5, "depth": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert {node["type"] for node in body["nodes"]} <= {"producer", "band"}
    assert any(edge["layer"] == "producer_band" for edge in body["edges"])
    assert body["meta"]["limits"]["max_nodes"] == 500
