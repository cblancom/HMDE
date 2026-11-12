from __future__ import annotations

from collections import Counter

import pytest

from hmde.services import producers as producers_service


def _overview(api_client, run_id, **params):
    query = {"analysis_run": str(run_id)}
    query.update(params)
    return api_client.get("/api/v1/graph/producers", params=query)


def test_overview_bands_view_uses_shared_band_nodes(api_client, network_analysis_run) -> None:
    response = _overview(api_client, network_analysis_run, view="bands")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["scope"] == "overview"
    assert body["meta"]["view"] == "bands"
    assert body["meta"]["analysis_run_id"] == str(network_analysis_run)
    assert body["meta"]["limits"] == {
        "producer_limit": 0,
        "max_nodes": 1000,
        "max_edges": 2000,
    }
    assert {node["type"] for node in body["nodes"]} <= {"producer", "band"}
    assert body["edges"]
    assert all(edge["layer"] == "producer_band" for edge in body["edges"])

    node_ids = [node["id"] for node in body["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    pairs = [(edge["source"], edge["target"]) for edge in body["edges"]]
    assert len(pairs) == len(set(pairs))

    target_counts = Counter(edge["target"] for edge in body["edges"])
    assert target_counts.most_common(1)[0][1] >= 2

    producer_ids = {node["id"] for node in body["nodes"] if node["type"] == "producer"}
    assert all(
        not (edge["source"] in producer_ids and edge["target"] in producer_ids)
        for edge in body["edges"]
    )


def test_overview_albums_view_keeps_album_nodes(api_client, network_analysis_run) -> None:
    response = _overview(api_client, network_analysis_run, view="albums")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["view"] == "albums"
    assert {node["type"] for node in body["nodes"]} <= {"producer", "album"}
    assert body["edges"]
    assert all(edge["layer"] == "producer_album" for edge in body["edges"])
    album_nodes = [node for node in body["nodes"] if node["type"] == "album"]
    assert album_nodes
    assert all(
        "year" in node["attributes"] and "decade" in node["attributes"] for node in album_nodes
    )


def test_overview_isolated_toggle_and_top_k(api_client, network_analysis_run) -> None:
    visible = _overview(api_client, network_analysis_run, view="bands", include_isolated="true")
    hidden = _overview(api_client, network_analysis_run, view="bands", include_isolated="false")
    assert visible.status_code == 200
    assert hidden.status_code == 200
    assert visible.json()["meta"]["include_isolated"] is True
    assert hidden.json()["meta"]["include_isolated"] is False
    assert (
        hidden.json()["meta"]["selected_producers"] < visible.json()["meta"]["selected_producers"]
    )

    top = _overview(
        api_client,
        network_analysis_run,
        view="bands",
        producer_limit=5,
        producer_sort="album_count",
        order="desc",
    )
    assert top.status_code == 200
    meta = top.json()["meta"]
    assert meta["selected_producers"] == 5
    assert meta["matched_producers"] > meta["selected_producers"]
    assert meta["truncated"] is True


def test_overview_album_filters_and_caps(api_client, network_analysis_run) -> None:
    filtered = _overview(api_client, network_analysis_run, view="albums", decade="1990s")
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["meta"]["matched_producers"] > 0
    assert body["edges"]
    nodes = {node["id"]: node for node in body["nodes"]}
    assert all(nodes[edge["target"]]["attributes"]["decade"] == "1990s" for edge in body["edges"])

    node_capped = _overview(
        api_client, network_analysis_run, view="bands", max_nodes=10, max_edges=1000
    )
    assert node_capped.status_code == 200
    assert len(node_capped.json()["nodes"]) <= 10
    assert node_capped.json()["meta"]["truncated"] is True

    edge_capped = _overview(
        api_client, network_analysis_run, view="albums", max_nodes=1000, max_edges=5
    )
    assert edge_capped.status_code == 200
    assert len(edge_capped.json()["edges"]) == 5
    assert edge_capped.json()["meta"]["truncated"] is True


def test_overview_layouts_are_optional_and_deterministic(api_client, network_analysis_run) -> None:
    default = _overview(api_client, network_analysis_run, view="albums")
    assert default.status_code == 200
    assert default.json().get("layout") is None

    bipartite = _overview(api_client, network_analysis_run, view="albums", layout="bipartite")
    assert bipartite.status_code == 200
    body = bipartite.json()
    layout = body["layout"]
    assert layout["algorithm"] == "bipartite"
    assert {item["id"] for item in layout["nodes"]} == {node["id"] for node in body["nodes"]}
    nodes = {node["id"]: node for node in body["nodes"]}
    producer_ids = {node_id for node_id, node in nodes.items() if node["type"] == "producer"}
    target_ids = {node_id for node_id, node in nodes.items() if node["type"] == "album"}
    positions = {item["id"]: (item["x"], item["y"]) for item in layout["nodes"]}
    assert all(
        positions[producer][0] < positions[target][0]
        for producer in producer_ids
        for target in target_ids
    )
    assert (
        layout
        == _overview(api_client, network_analysis_run, view="albums", layout="bipartite").json()[
            "layout"
        ]
    )

    community = _overview(api_client, network_analysis_run, view="bands", layout="community")
    assert community.status_code == 200
    community_layout = community.json()["layout"]
    assert community_layout["algorithm"] == "community"
    assert {item["id"] for item in community_layout["nodes"]} == {
        node["id"] for node in community.json()["nodes"]
    }


def test_overview_layout_failure_keeps_the_graph(
    api_client, network_analysis_run, monkeypatch
) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("layout failed")

    monkeypatch.setattr(producers_service, "compute_community_layout", fail)
    response = _overview(api_client, network_analysis_run, view="bands", layout="community")
    assert response.status_code == 200
    assert response.json()["layout"] is None


def test_overview_rejects_invalid_parameters(api_client, network_analysis_run) -> None:
    assert _overview(api_client, network_analysis_run, view="mixed").status_code == 422
    assert _overview(api_client, network_analysis_run, producer_limit=1001).status_code == 422
    assert _overview(api_client, network_analysis_run, max_nodes=0).status_code == 422
    assert _overview(api_client, network_analysis_run, max_edges=2001).status_code == 422
    assert _overview(api_client, network_analysis_run, decade="1980").status_code == 422
    assert _overview(api_client, network_analysis_run, layout="mixed").status_code == 422

    missing = api_client.get(
        "/api/v1/graph/producers",
        params={"analysis_run": "00000000-0000-0000-0000-000000000000"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Analysis run not found"


@pytest.mark.parametrize("view", ["bands", "albums"])
def test_overview_default_run(api_client, network_analysis_run, view: str) -> None:
    response = api_client.get("/api/v1/graph/producers", params={"view": view})
    assert response.status_code == 200
    assert response.json()["meta"]["analysis_run_id"] == str(network_analysis_run)
