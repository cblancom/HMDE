from __future__ import annotations

from uuid import UUID

from hmde.services.graph_layouts import (
    UNASSIGNED_COMMUNITY,
    community_assignments,
    compute_bipartite_layout,
    compute_community_layout,
)

P1 = UUID(int=1)
P2 = UUID(int=2)
P3 = UUID(int=3)
P4 = UUID(int=4)
P5 = UUID(int=5)
T1 = UUID(int=11)
T2 = UUID(int=12)
T3 = UUID(int=13)
T4 = UUID(int=14)

PRODUCERS = {P1, P2, P3, P4, P5}
NODES = PRODUCERS | {T1, T2, T3, T4}
EDGES = [
    (P1, T1),
    (P2, T1),
    (P2, T2),
    (P3, T2),
    (P3, T3),
    (P4, T3),
]
COMMUNITIES = {
    P1: "community-000",
    P2: "community-000",
    P3: "community-001",
    P4: "community-001",
}


def test_bipartite_layout_places_producers_left_of_targets() -> None:
    positions = compute_bipartite_layout(NODES, PRODUCERS, EDGES)

    assert set(positions) == NODES
    assert all(isinstance(value, tuple) and len(value) == 2 for value in positions.values())
    assert all(0 <= value[0] <= 1000 and 0 <= value[1] <= 1000 for value in positions.values())
    assert all(
        positions[producer][0] < positions[target][0]
        for producer in PRODUCERS
        for target in {T1, T2, T3, T4}
    )
    assert positions == compute_bipartite_layout(NODES, PRODUCERS, EDGES)


def test_bipartite_layout_handles_isolated_nodes_and_empty_graphs() -> None:
    positions = compute_bipartite_layout(NODES, PRODUCERS, [(P1, T1)])

    assert set(positions) == NODES
    assert positions == compute_bipartite_layout(NODES, PRODUCERS, [(P1, T1)])
    assert compute_bipartite_layout([], set(), []) == {}


def test_community_assignments_use_majority_then_key_tiebreak() -> None:
    assignments = community_assignments(NODES, PRODUCERS, EDGES, COMMUNITIES)

    assert assignments[T1] == "community-000"
    assert assignments[T2] == "community-000"
    assert assignments[T3] == "community-001"
    assert assignments[T4] == UNASSIGNED_COMMUNITY
    assert assignments[P5] == UNASSIGNED_COMMUNITY


def test_community_layout_is_deterministic_and_covers_every_node() -> None:
    positions = compute_community_layout(NODES, PRODUCERS, EDGES, COMMUNITIES)

    assert set(positions) == NODES
    assert all(0 <= value[0] <= 1000 and 0 <= value[1] <= 1000 for value in positions.values())
    assert positions == compute_community_layout(NODES, PRODUCERS, EDGES, COMMUNITIES)


def test_community_layout_handles_one_community_and_no_edges() -> None:
    one = {producer: "community-000" for producer in PRODUCERS}
    positions = compute_community_layout(NODES, PRODUCERS, [], one)

    assert set(positions) == NODES
    assert positions == compute_community_layout(NODES, PRODUCERS, [], one)
    assert compute_community_layout([], set(), [], {}) == {}
