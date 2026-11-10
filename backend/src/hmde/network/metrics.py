"""Network metrics for the producer-centric graph layers."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import networkx as nx
from networkx.algorithms import community as nx_community

from .graph import PRODUCER_ALBUM, PRODUCER_BAND, ProducerAlbumLayer, ProducerBandLayer
from .loader import NetworkData

TOP_K = 20
COMMUNITY_SEED = 42
COMMUNITY_RESOLUTION = 1.0


@dataclass(frozen=True, slots=True)
class NodeMetricSpec:
    node_key: str
    layer_code: str
    metric_code: str
    value: float
    numerator: float | None
    denominator: float | None
    unit: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProducerMetricSpec:
    producer_id: uuid.UUID
    metric_code: str
    value: float
    numerator: float | None
    denominator: float | None
    unit: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TemporalMetricSpec:
    layer_code: str
    scope_type: str
    scope_key: str
    metric_code: str
    numerator: float | None
    denominator: float | None
    value: float
    unit: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CommunitySpec:
    community_key: str
    algorithm: str
    resolution: float
    size: int
    details: dict[str, Any]
    member_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MetricsPayload:
    node_metrics: tuple[NodeMetricSpec, ...]
    producer_metrics: tuple[ProducerMetricSpec, ...]
    temporal_metrics: tuple[TemporalMetricSpec, ...]
    communities: tuple[CommunitySpec, ...]
    graph_counts: dict[str, Any]
    support_summary: dict[str, int]
    top_albums: tuple[dict[str, Any], ...]
    top_bands: tuple[dict[str, Any], ...]
    advisories: tuple[str, ...]


def compute_metrics(
    data: NetworkData,
    album_layer: ProducerAlbumLayer,
    band_layer: ProducerBandLayer,
    *,
    top_k: int = TOP_K,
) -> MetricsPayload:
    node_metrics: list[NodeMetricSpec] = []
    producer_metrics: list[ProducerMetricSpec] = []
    temporal_metrics: list[TemporalMetricSpec] = []
    advisories: list[str] = []

    album_counts = _producer_album_counts(data)
    band_counts = _producer_band_counts(band_layer)
    labels = _producer_labels(album_layer)
    producer_ids = sorted(set(album_counts) | set(band_counts), key=str)

    total_album_assignments = sum(album_counts.values())
    total_band_edges = sum(band_counts.values())
    album_shares = _shares(album_counts)
    band_shares = _shares(band_counts)

    for producer_id in producer_ids:
        label = labels.get(producer_id, str(producer_id))
        album_count = album_counts.get(producer_id, 0)
        band_count = band_counts.get(producer_id, 0)
        self_count = band_layer.self_produced_albums.get(producer_id, 0)
        producer_metrics.append(
            _producer_metric(
                producer_id,
                "NA-PROD-001",
                album_count,
                total_album_assignments,
                details={"producer": label},
            )
        )
        producer_metrics.append(
            _producer_metric(
                producer_id,
                "NA-PROD-002",
                band_count,
                total_band_edges,
                details={"producer": label},
            )
        )
        producer_metrics.append(
            _producer_metric(
                producer_id,
                "NA-PROD-003",
                self_count,
                album_count,
                details={"producer": label, "meaning": "self-produced albums"},
            )
        )

    for graph, layer in (
        (album_layer.graph, PRODUCER_ALBUM),
        (band_layer.graph, PRODUCER_BAND),
    ):
        for node_key in sorted(graph.nodes):
            degree = float(graph.degree(node_key))
            weighted = float(sum(edge.get("weight", 1.0) for edge in graph[node_key].values()))
            node_metrics.append(
                NodeMetricSpec(
                    node_key=node_key,
                    layer_code=layer,
                    metric_code="NA-DEG-001",
                    value=degree,
                    numerator=degree,
                    denominator=float(max(1, graph.number_of_nodes() - 1)),
                    unit="count",
                    details={"normalization": "raw degree"},
                )
            )
            node_metrics.append(
                NodeMetricSpec(
                    node_key=node_key,
                    layer_code=layer,
                    metric_code="NA-WDEG-001",
                    value=weighted,
                    numerator=weighted,
                    denominator=None,
                    unit="count",
                    details={"weight": "simple edge weight"},
                )
            )

    betweenness = nx.betweenness_centrality(band_layer.graph, normalized=True)
    for node_key in sorted(betweenness):
        value = float(betweenness[node_key])
        node_metrics.append(
            NodeMetricSpec(
                node_key=node_key,
                layer_code=PRODUCER_BAND,
                metric_code="NA-BET-001",
                value=value,
                numerator=None,
                denominator=None,
                unit="ratio",
                details={"normalization": "networkx normalized betweenness"},
            )
        )
        if node_key.startswith("artist:"):
            producer_id = uuid.UUID(node_key.split(":", 1)[1])
            if producer_id in producer_ids:
                producer_metrics.append(
                    _producer_metric(
                        producer_id,
                        "NA-BET-001",
                        value,
                        None,
                        details={"normalization": "networkx normalized betweenness"},
                    )
                )

    communities = _communities(data, labels)
    temporal_metrics.extend(_global_concentration(album_shares, band_shares, top_k))
    temporal_metrics.extend(_temporal_metrics(data, album_layer, band_layer))
    graph_counts = _graph_counts(album_layer, band_layer)
    support_summary = _support_summary(album_layer)
    top_albums = _top_producers(album_counts, album_shares, labels, top_k)
    top_bands = _top_producers(band_counts, band_shares, labels, top_k)
    if graph_counts["producer_album"]["components"] > 1:
        advisories.append("producer–album layer has multiple connected components")
    if graph_counts["producer_band"]["components"] > 1:
        advisories.append("producer–band layer has multiple connected components")
    if support_summary["unknown"] > 0:
        advisories.append("some producer–album edges have no support denominator")

    return MetricsPayload(
        node_metrics=tuple(node_metrics),
        producer_metrics=tuple(producer_metrics),
        temporal_metrics=tuple(temporal_metrics),
        communities=communities,
        graph_counts=graph_counts,
        support_summary=support_summary,
        top_albums=top_albums,
        top_bands=top_bands,
        advisories=tuple(advisories),
    )


def _producer_album_counts(data: NetworkData) -> dict[uuid.UUID, int]:
    albums: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for row in data.producer_albums:
        albums[row.producer_id].add(row.album_id)
    return {producer_id: len(ids) for producer_id, ids in albums.items()}


def _producer_band_counts(band_layer: ProducerBandLayer) -> dict[uuid.UUID, int]:
    counts: dict[uuid.UUID, int] = {}
    for edge in band_layer.edges:
        producer_id = uuid.UUID(edge.source_key.split(":", 1)[1])
        counts[producer_id] = counts.get(producer_id, 0) + 1
    return counts


def _producer_labels(album_layer: ProducerAlbumLayer) -> dict[uuid.UUID, str]:
    labels: dict[uuid.UUID, str] = {}
    for node in album_layer.nodes:
        if node.node_type == "artist":
            labels[uuid.UUID(node.node_key.split(":", 1)[1])] = node.label
    return labels


def _shares(counts: dict[uuid.UUID, int]) -> dict[uuid.UUID, float]:
    total = sum(counts.values())
    if total == 0:
        return {key: 0.0 for key in counts}
    return {key: value / total for key, value in counts.items()}


def _producer_metric(
    producer_id: uuid.UUID,
    code: str,
    value: float,
    denominator: float | None,
    *,
    details: dict[str, Any],
) -> ProducerMetricSpec:
    return ProducerMetricSpec(
        producer_id=producer_id,
        metric_code=code,
        value=float(value),
        numerator=float(value),
        denominator=denominator,
        unit="count" if code != "NA-BET-001" else "ratio",
        details=details,
    )


def _global_concentration(
    album_shares: dict[uuid.UUID, float],
    band_shares: dict[uuid.UUID, float],
    top_k: int,
) -> list[TemporalMetricSpec]:
    rows: list[TemporalMetricSpec] = []
    for layer, shares, code_prefix in (
        (PRODUCER_ALBUM, album_shares, "album"),
        (PRODUCER_BAND, band_shares, "band"),
    ):
        ordered = sorted(shares.values(), reverse=True)
        top_share = sum(ordered[:top_k])
        hhi = sum(value**2 for value in ordered)
        cumulative = 0.0
        required = 0
        for value in ordered:
            cumulative += value
            required += 1
            if cumulative >= 0.5:
                break
        rows.extend(
            [
                _temporal(
                    layer,
                    "global",
                    "all",
                    f"NA-CONC-{'001' if code_prefix == 'album' else '004'}",
                    top_share,
                    len(ordered),
                    details={"k": top_k},
                ),
                _temporal(
                    layer,
                    "global",
                    "all",
                    f"NA-CONC-{'002' if code_prefix == 'album' else '005'}",
                    hhi,
                    len(ordered),
                    details={"formula": "sum of squared shares"},
                ),
                _temporal(
                    layer,
                    "global",
                    "all",
                    f"NA-CONC-{'003' if code_prefix == 'album' else '006'}",
                    float(required),
                    len(ordered),
                    details={"threshold": 0.5},
                ),
            ]
        )
    return rows


def _temporal_metrics(
    data: NetworkData,
    album_layer: ProducerAlbumLayer,
    band_layer: ProducerBandLayer,
) -> list[TemporalMetricSpec]:
    rows: list[TemporalMetricSpec] = []
    album_by_decade: dict[str, set[uuid.UUID]] = defaultdict(set)
    producer_by_decade: dict[str, set[uuid.UUID]] = defaultdict(set)
    band_by_decade: dict[str, set[uuid.UUID]] = defaultdict(set)
    producer_album_by_decade: dict[str, dict[uuid.UUID, set[uuid.UUID]]] = defaultdict(
        lambda: defaultdict(set)
    )
    producer_band_by_decade: dict[str, dict[uuid.UUID, set[uuid.UUID]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for row in data.producer_albums:
        album = data.albums[row.album_id]
        if album.first_release_date is None:
            continue
        decade = f"{(album.first_release_date.year // 10) * 10}s"
        album_by_decade[decade].add(row.album_id)
        producer_by_decade[decade].add(row.producer_id)
        producer_album_by_decade[decade][row.producer_id].add(row.album_id)
    for edge in band_layer.edges:
        album_ids = [uuid.UUID(value) for value in edge.evidence["album_ids"]]
        producer_id = uuid.UUID(edge.source_key.split(":", 1)[1])
        for album_id in album_ids:
            album = data.albums[album_id]
            if album.first_release_date is None:
                continue
            decade = f"{(album.first_release_date.year // 10) * 10}s"
            band_by_decade[decade].add(album.band_id)
            producer_band_by_decade[decade][producer_id].add(album.band_id)

    for decade in sorted(set(album_by_decade) | set(producer_by_decade) | set(band_by_decade)):
        album_counts = {key: len(value) for key, value in producer_album_by_decade[decade].items()}
        band_counts = {key: len(value) for key, value in producer_band_by_decade[decade].items()}
        album_shares = _shares(album_counts)
        band_shares = _shares(band_counts)
        rows.extend(
            [
                _temporal(
                    PRODUCER_ALBUM,
                    "decade",
                    decade,
                    "NA-TIME-001",
                    len(producer_by_decade[decade]),
                    None,
                ),
                _temporal(
                    PRODUCER_ALBUM,
                    "decade",
                    decade,
                    "NA-TIME-002",
                    len(album_by_decade[decade]),
                    None,
                ),
                _temporal(
                    PRODUCER_ALBUM,
                    "decade",
                    decade,
                    "NA-CONC-001",
                    sum(sorted(album_shares.values(), reverse=True)[:TOP_K]),
                    len(album_shares),
                    details={"k": TOP_K},
                ),
                _temporal(
                    PRODUCER_ALBUM,
                    "decade",
                    decade,
                    "NA-CONC-002",
                    sum(value**2 for value in album_shares.values()),
                    len(album_shares),
                ),
                _temporal(
                    PRODUCER_BAND,
                    "decade",
                    decade,
                    "NA-TIME-003",
                    len(band_by_decade[decade]),
                    None,
                ),
                _temporal(
                    PRODUCER_BAND,
                    "decade",
                    decade,
                    "NA-TIME-004",
                    len(producer_band_by_decade[decade]),
                    None,
                ),
                _temporal(
                    PRODUCER_BAND,
                    "decade",
                    decade,
                    "NA-CONC-004",
                    sum(sorted(band_shares.values(), reverse=True)[:TOP_K]),
                    len(band_shares),
                    details={"k": TOP_K},
                ),
                _temporal(
                    PRODUCER_BAND,
                    "decade",
                    decade,
                    "NA-CONC-005",
                    sum(value**2 for value in band_shares.values()),
                    len(band_shares),
                ),
            ]
        )
    return rows


def _temporal(
    layer: str,
    scope_type: str,
    scope_key: str,
    code: str,
    value: float,
    denominator: float | None,
    *,
    details: dict[str, Any] | None = None,
) -> TemporalMetricSpec:
    return TemporalMetricSpec(
        layer_code=layer,
        scope_type=scope_type,
        scope_key=scope_key,
        metric_code=code,
        numerator=float(value),
        denominator=float(denominator) if denominator is not None else None,
        value=float(value),
        unit="count",
        details=details or {},
    )


def _graph_counts(
    album_layer: ProducerAlbumLayer,
    band_layer: ProducerBandLayer,
) -> dict[str, Any]:
    return {
        "producer_album": {
            "nodes": album_layer.graph.number_of_nodes(),
            "edges": album_layer.graph.number_of_edges(),
            "components": nx.number_connected_components(album_layer.graph),
        },
        "producer_band": {
            "nodes": band_layer.graph.number_of_nodes(),
            "edges": band_layer.graph.number_of_edges(),
            "components": nx.number_connected_components(band_layer.graph),
        },
    }


def _support_summary(album_layer: ProducerAlbumLayer) -> dict[str, int]:
    full = sum(1 for edge in album_layer.edges if edge.support_ratio == 1.0)
    partial = sum(
        1
        for edge in album_layer.edges
        if edge.support_ratio is not None and edge.support_ratio < 1.0
    )
    unknown = sum(1 for edge in album_layer.edges if edge.support_ratio is None)
    return {"full": full, "partial": partial, "unknown": unknown}


def _top_producers(
    counts: dict[uuid.UUID, int],
    shares: dict[uuid.UUID, float],
    labels: dict[uuid.UUID, str],
    top_k: int,
) -> tuple[dict[str, Any], ...]:
    ordered = sorted(
        counts.items(), key=lambda item: (-item[1], labels.get(item[0], str(item[0])), str(item[0]))
    )
    return tuple(
        {
            "producer_id": str(producer_id),
            "producer": labels.get(producer_id, str(producer_id)),
            "count": count,
            "share": shares.get(producer_id, 0.0),
        }
        for producer_id, count in ordered[:top_k]
    )


def _communities(
    data: NetworkData,
    labels: dict[uuid.UUID, str],
) -> tuple[CommunitySpec, ...]:
    albums_to_producers: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for row in data.producer_albums:
        albums_to_producers[row.album_id].add(row.producer_id)
    projection = nx.Graph()
    for producer_id in sorted({row.producer_id for row in data.producer_albums}, key=str):
        projection.add_node(producer_id)
    for producers in albums_to_producers.values():
        ordered = sorted(producers, key=str)
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if projection.has_edge(first, second):
                    projection[first][second]["weight"] += 1
                else:
                    projection.add_edge(first, second, weight=1)
    if projection.number_of_nodes() == 0:
        return ()
    raw = nx_community.louvain_communities(
        projection,
        weight="weight",
        resolution=COMMUNITY_RESOLUTION,
        seed=COMMUNITY_SEED,
    )
    ordered_communities = sorted(
        (tuple(sorted(members, key=str)) for members in raw),
        key=lambda members: (min(str(member) for member in members), len(members)),
    )
    result: list[CommunitySpec] = []
    for index, members in enumerate(ordered_communities):
        member_keys = tuple(f"artist:{member}" for member in members)
        result.append(
            CommunitySpec(
                community_key=f"community-{index:03d}",
                algorithm="louvain",
                resolution=COMMUNITY_RESOLUTION,
                size=len(members),
                details={
                    "members": [labels.get(member, str(member)) for member in members],
                    "seed": COMMUNITY_SEED,
                },
                member_keys=member_keys,
            )
        )
    return tuple(result)
