"""Deterministic graph layout calculations for the global producer overview."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from math import ceil, cos, pi, sin, sqrt
from uuid import UUID

import networkx as nx

UNASSIGNED_COMMUNITY = "unassigned"
LAYOUT_BOX = 1000.0
LAYOUT_MARGIN = 80.0
COMMUNITY_SEED = 42

PositionMap = dict[UUID, tuple[float, float]]


def compute_bipartite_layout(
    node_ids: Iterable[UUID],
    producer_ids: set[UUID],
    edges: Iterable[tuple[UUID, UUID]],
) -> PositionMap:
    """Return deterministic producer-left/target-right positions."""
    nodes = sorted(set(node_ids), key=str)
    edge_rows = list(edges)
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edge_rows)
    try:
        raw = nx.bipartite_layout(
            graph,
            nodes=sorted(producer_ids, key=str),
            align="vertical",
            scale=1.0,
        )
        positions = {node_id: (float(raw[node_id][0]), 0.0) for node_id in nodes}
    except (KeyError, nx.NetworkXError, ValueError):
        positions = {node_id: (-1.0 if node_id in producer_ids else 1.0, 0.0) for node_id in nodes}

    producers = [node_id for node_id in nodes if node_id in producer_ids]
    targets = [node_id for node_id in nodes if node_id not in producer_ids]
    for group in (producers, targets):
        for index, node_id in enumerate(group):
            if group:
                positions[node_id] = (
                    positions[node_id][0],
                    _spaced_value(index, len(group)),
                )
    return _normalize(positions, uniform=False)


def community_assignments(
    node_ids: Iterable[UUID],
    producer_ids: set[UUID],
    edges: Iterable[tuple[UUID, UUID]],
    community_by_producer: Mapping[UUID, str],
) -> dict[UUID, str]:
    """Assign every node to a producer community, using target-majority ties."""
    nodes = set(node_ids)
    assignments: dict[UUID, str] = {}
    for node_id in nodes:
        if node_id in producer_ids:
            assignments[node_id] = community_by_producer.get(node_id, UNASSIGNED_COMMUNITY)

    target_communities: dict[UUID, Counter[str]] = defaultdict(Counter)
    for source_id, target_id in edges:
        if source_id in producer_ids and target_id in nodes:
            target_communities[target_id][
                community_by_producer.get(source_id, UNASSIGNED_COMMUNITY)
            ] += 1

    for node_id in nodes:
        if node_id in assignments:
            continue
        counts = target_communities.get(node_id)
        assignments[node_id] = (
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
            if counts
            else UNASSIGNED_COMMUNITY
        )
    return assignments


def compute_community_layout(
    node_ids: Iterable[UUID],
    producer_ids: set[UUID],
    edges: Iterable[tuple[UUID, UUID]],
    community_by_producer: Mapping[UUID, str],
) -> PositionMap:
    """Return clustered positions for the persisted producer communities."""
    nodes = sorted(set(node_ids), key=str)
    edge_rows = list(edges)
    assignments = community_assignments(nodes, producer_ids, edge_rows, community_by_producer)
    members: dict[str, dict[str, list[UUID]]] = defaultdict(
        lambda: {"producers": [], "targets": []}
    )
    for node_id in nodes:
        group = "producers" if node_id in producer_ids else "targets"
        members[assignments[node_id]][group].append(node_id)
    for group in members.values():
        group["producers"].sort(key=str)
        group["targets"].sort(key=str)

    community_keys = sorted(members)
    contracted = nx.Graph()
    contracted.add_nodes_from(community_keys)
    shared_targets: dict[UUID, set[str]] = defaultdict(set)
    for source_id, target_id in edge_rows:
        if source_id in producer_ids:
            shared_targets[target_id].add(
                community_by_producer.get(source_id, UNASSIGNED_COMMUNITY)
            )
    for keys in shared_targets.values():
        ordered = sorted(keys)
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if contracted.has_edge(first, second):
                    contracted[first][second]["weight"] += 1
                else:
                    contracted.add_edge(first, second, weight=1)

    centers = _community_centers(contracted)
    positions: PositionMap = {}
    for community_key in community_keys:
        center = centers[community_key]
        producer_group = members[community_key]["producers"]
        target_group = members[community_key]["targets"]
        count = len(producer_group) + len(target_group)
        radius = min(80.0, 18.0 + 7.0 * sqrt(max(count, 1)))
        _place_ring(positions, producer_group, center, radius * 0.45, 0.0)
        _place_ring(positions, target_group, center, radius, pi / 4)
    return _normalize(positions)


def _community_centers(contracted: nx.Graph) -> dict[str, tuple[float, float]]:
    keys = sorted(contracted)
    if not keys:
        return {}
    if len(keys) == 1 or contracted.number_of_edges() == 0:
        columns = max(1, ceil(sqrt(len(keys))))
        rows = max(1, ceil(len(keys) / columns))
        return {
            key: (
                _spaced_value(index % columns, columns),
                _spaced_value(index // columns, rows),
            )
            for index, key in enumerate(keys)
        }
    raw = nx.spring_layout(
        contracted,
        seed=COMMUNITY_SEED,
        weight="weight",
        scale=1.0,
    )
    return _normalize({key: (float(raw[key][0]), float(raw[key][1])) for key in keys})


def _place_ring(
    positions: PositionMap,
    members: list[UUID],
    center: tuple[float, float],
    radius: float,
    start_angle: float,
) -> None:
    if not members:
        return
    for index, node_id in enumerate(members):
        angle = start_angle + (2 * pi * index / len(members))
        positions[node_id] = (
            center[0] + radius * cos(angle),
            center[1] + radius * sin(angle),
        )


def _spaced_value(index: int, count: int) -> float:
    if count <= 1:
        return LAYOUT_BOX / 2
    return LAYOUT_MARGIN + (LAYOUT_BOX - 2 * LAYOUT_MARGIN) * index / (count - 1)


def _normalize[NodeKey](
    positions: Mapping[NodeKey, tuple[float, float]],
    *,
    uniform: bool = True,
) -> dict[NodeKey, tuple[float, float]]:
    if not positions:
        return {}
    xs = [value[0] for value in positions.values()]
    ys = [value[1] for value in positions.values()]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    span = max(width, height)
    if span == 0:
        return {node_id: (LAYOUT_BOX / 2, LAYOUT_BOX / 2) for node_id in positions}
    scale = (LAYOUT_BOX - 2 * LAYOUT_MARGIN) / span if uniform else None
    scale_x = scale or ((LAYOUT_BOX - 2 * LAYOUT_MARGIN) / width if width else 1.0)
    scale_y = scale or ((LAYOUT_BOX - 2 * LAYOUT_MARGIN) / height if height else 1.0)
    return {
        node_id: (
            round(LAYOUT_MARGIN + (x - min(xs)) * scale_x, 3),
            round(LAYOUT_MARGIN + (y - min(ys)) * scale_y, 3),
        )
        for node_id, (x, y) in positions.items()
    }
