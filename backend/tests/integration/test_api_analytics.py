from __future__ import annotations


def test_analysis_run_summary_and_decades(api_client, network_analysis_run) -> None:
    runs = api_client.get("/api/v1/analysis-runs")
    assert runs.status_code == 200
    assert runs.json()["total"] >= 1
    assert any(
        item["analysis_run_id"] == str(network_analysis_run) for item in runs.json()["items"]
    )

    detail = api_client.get(f"/api/v1/analysis-runs/{network_analysis_run}")
    assert detail.status_code == 200
    assert detail.json()["status"] in {"completed", "completed_with_limitations"}

    summary = api_client.get("/api/v1/analytics/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["meta"]["analysis_run_id"] == str(network_analysis_run)
    assert "producer_album" in body["graph_counts"]
    assert body["community_count"] > 0

    decades = api_client.get("/api/v1/analytics/decades")
    assert decades.status_code == 200
    assert decades.json()["items"]
    assert all(item["scope_key"].endswith("s") for item in decades.json()["items"])
