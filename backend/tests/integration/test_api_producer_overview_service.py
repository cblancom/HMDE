from __future__ import annotations

import uuid
from collections import Counter

from sqlalchemy import select

from hmde.models import AnalysisRun, GraphEdge, GraphNode
from hmde.services.producers import get_producer_overview_graph, list_producers


def _service_graph(session, run, **overrides):
    parameters = {
        "view": "bands",
        "producer_limit": 0,
        "producer_sort": "album_count",
        "order": "desc",
        "decade": None,
        "subgenre": None,
        "include_isolated": True,
        "include_evidence": True,
        "max_nodes": 1000,
        "max_edges": 2000,
    }
    parameters.update(overrides)
    return get_producer_overview_graph(session, run, **parameters)


def _run(session, run_id):
    run = session.get(AnalysisRun, run_id)
    assert run is not None
    return run


def test_bands_overview_uses_shared_band_nodes(
    seeded_session_factory, network_analysis_run
) -> None:
    with seeded_session_factory() as session:
        run = _run(session, network_analysis_run)
        graph = _service_graph(session, run, view="bands")

    assert graph.meta.scope == "overview"
    assert graph.meta.view == "bands"
    assert graph.meta.analysis_run_id == run.id
    assert graph.meta.analysis_version == run.analysis_version
    assert graph.meta.dataset_version == run.dataset_version
    assert graph.meta.taxonomy_version == run.taxonomy_version
    assert graph.meta.graph_version == run.graph_version
    assert graph.meta.limits.max_nodes == 1000
    assert graph.meta.limits.max_edges == 2000
    assert {node.type for node in graph.nodes} <= {"producer", "band"}
    assert all(edge.layer == "producer_band" for edge in graph.edges)

    node_ids = [node.id for node in graph.nodes]
    assert len(node_ids) == len(set(node_ids))

    pairs = [(edge.source, edge.target) for edge in graph.edges]
    assert len(pairs) == len(set(pairs))

    target_counts = Counter(edge.target for edge in graph.edges)
    shared_target, degree = target_counts.most_common(1)[0]
    assert degree >= 2
    assert sum(1 for node in graph.nodes if node.id == shared_target) == 1

    producer_ids = {node.id for node in graph.nodes if node.type == "producer"}
    assert all(
        not (edge.source in producer_ids and edge.target in producer_ids) for edge in graph.edges
    )

    band_producers = [
        node for node in graph.nodes if node.type == "band" and "producer" in node.roles
    ]
    assert band_producers
    assert all("band_count" in node.attributes for node in band_producers)
    assert any(node.attributes["band_count"] == 0 for node in band_producers)


def test_albums_overview_deduplicates_roles_and_keeps_album_nodes(
    seeded_session_factory, network_analysis_run
) -> None:
    with seeded_session_factory() as session:
        run = _run(session, network_analysis_run)
        graph = _service_graph(session, run, view="albums")
        assert {node.type for node in graph.nodes} <= {"producer", "album"}
        assert all(edge.layer == "producer_album" for edge in graph.edges)

        nodes_by_id = {node.id: node for node in session.scalars(select(GraphNode))}
        existing = next(
            edge
            for edge in session.scalars(
                select(GraphEdge).where(
                    GraphEdge.analysis_run_id == run.id,
                    GraphEdge.layer_code == "producer_album",
                )
            )
        )
        new_role = "co-producer" if existing.role_code != "co-producer" else "producer"
        session.add(
            GraphEdge(
                id=uuid.uuid4(),
                analysis_run_id=run.id,
                layer_code="producer_album",
                source_node_id=existing.source_node_id,
                target_node_id=existing.target_node_id,
                role_code=new_role,
                weight=1.0,
                support_ratio=0.5,
                evidence={"synthetic": True},
            )
        )
        session.flush()
        try:
            graph = _service_graph(session, run, view="albums", include_evidence=True)
            source_entity = nodes_by_id[existing.source_node_id].entity_id
            target_entity = nodes_by_id[existing.target_node_id].entity_id
            merged = [
                edge
                for edge in graph.edges
                if edge.source == source_entity and edge.target == target_entity
            ]
            assert len(merged) == 1
            assert merged[0].role == "mixed"
            roles = merged[0].evidence["roles"]
            assert isinstance(roles, list)
            assert set(roles) == {existing.role_code, new_role}
        finally:
            session.rollback()


def test_overview_isolated_toggle_and_counts(seeded_session_factory, network_analysis_run) -> None:
    with seeded_session_factory() as session:
        run = _run(session, network_analysis_run)
        isolated_id = uuid.uuid4()
        session.add(
            GraphNode(
                id=uuid.uuid4(),
                analysis_run_id=run.id,
                node_key=f"artist:synthetic-isolated-{isolated_id}",
                node_type="artist",
                entity_id=isolated_id,
                mbid=None,
                label="Synthetic Isolated Producer",
                roles=["producer"],
                attributes={"artist_type": "person", "country": None},
            )
        )
        session.flush()
        try:
            with_isolated = _service_graph(session, run, view="bands", include_isolated=True)
            without_isolated = _service_graph(session, run, view="bands", include_isolated=False)
        finally:
            session.rollback()

    connected = {edge.source for edge in with_isolated.edges} | {
        edge.target for edge in with_isolated.edges
    }
    isolated = {
        node.id
        for node in with_isolated.nodes
        if node.type == "producer" and node.id not in connected
    }
    assert isolated == {isolated_id}
    assert with_isolated.meta.include_isolated is True
    assert without_isolated.meta.include_isolated is False
    assert without_isolated.meta.selected_producers < with_isolated.meta.selected_producers
    assert all(edge.source in connected for edge in without_isolated.edges)


def test_overview_top_k_sort_and_truncation(seeded_session_factory, network_analysis_run) -> None:
    with seeded_session_factory() as session:
        run = _run(session, network_analysis_run)
        graph = _service_graph(
            session,
            run,
            view="bands",
            producer_limit=5,
            producer_sort="album_count",
            order="desc",
        )
        ranking, matched = list_producers(
            session,
            run,
            q=None,
            decade=None,
            subgenre=None,
            sort="album_count",
            order="desc",
            limit=5,
            offset=0,
        )

    assert graph.meta.selected_producers == 5
    assert graph.meta.matched_producers == matched
    assert matched > graph.meta.selected_producers
    assert graph.meta.truncated is True
    assert {node.id for node in graph.nodes if node.type == "producer"} == {
        item.id for item in ranking
    }


def test_overview_album_filters_and_caps(seeded_session_factory, network_analysis_run) -> None:
    with seeded_session_factory() as session:
        run = _run(session, network_analysis_run)
        filtered = _service_graph(session, run, view="albums", decade="1990s")
        assert filtered.meta.matched_producers > 0
        assert filtered.edges
        for edge in filtered.edges:
            node = next(item for item in filtered.nodes if item.id == edge.target)
            assert node.attributes["decade"] == "1990s"

        node_capped = _service_graph(session, run, view="bands", max_nodes=10, max_edges=1000)
        assert len(node_capped.nodes) <= 10
        assert node_capped.meta.truncated is True

        edge_capped = _service_graph(session, run, view="albums", max_nodes=1000, max_edges=5)
        assert len(edge_capped.edges) == 5
        assert edge_capped.meta.truncated is True
