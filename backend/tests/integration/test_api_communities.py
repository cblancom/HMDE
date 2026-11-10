from __future__ import annotations


def test_community_list_and_detail(api_client, network_analysis_run) -> None:
    communities = api_client.get("/api/v1/communities", params={"limit": 200})
    assert communities.status_code == 200
    body = communities.json()
    assert body["total"] > 0
    assert body["meta"]["analysis_run_id"] == str(network_analysis_run)
    key = body["items"][0]["community_key"]

    detail = api_client.get(f"/api/v1/communities/{key}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["community_key"] == key
    assert detail_body["members"]

    missing = api_client.get("/api/v1/communities/community-missing")
    assert missing.status_code == 404
