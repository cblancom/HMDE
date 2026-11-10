"""Producer-centric graph construction and derivation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

import networkx as nx

from .loader import AlbumRow, NetworkData

PRODUCER_ALBUM = "producer_album"
PRODUCER_BAND = "producer_band"


@dataclass(frozen=True, slots=True)
class GraphNodeSpec:
    node_key: str
    node_type: str
    entity_id: uuid.UUID
    mbid: str | None
    label: str
    roles: tuple[str, ...]
    attributes: dict[str, Any]


@dataclass(frozen=True, slots=True)
class GraphEdgeSpec:
    layer_code: str
    source_key: str
    target_key: str
    role_code: str
    weight: float
    supporting_recordings: int | None
    album_recordings: int | None
    support_ratio: float | None
    scope_mix: dict[str, int]
    evidence: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProducerAlbumLayer:
    graph: nx.Graph
    nodes: tuple[GraphNodeSpec, ...]
    edges: tuple[GraphEdgeSpec, ...]


def artist_key(artist_id: uuid.UUID) -> str:
    return f"artist:{artist_id}"


def album_key(album_id: uuid.UUID) -> str:
    return f"album:{album_id}"


def build_producer_album_layer(data: NetworkData) -> ProducerAlbumLayer:
    nodes: dict[str, GraphNodeSpec] = {}
    album_roles: dict[uuid.UUID, set[str]] = {}
    albums = data.albums
    role_rows = data.producer_albums
    album_ids = {row.album_id for row in role_rows}
    for album_id in sorted(album_ids, key=str):
        album = albums[album_id]
        nodes[album_key(album_id)] = _album_node(album)

    producer_names: dict[uuid.UUID, str] = {}
    producer_mbids: dict[uuid.UUID, str] = {}
    producer_types: dict[uuid.UUID, str] = {}
    producer_countries: dict[uuid.UUID, str | None] = {}
    for row in role_rows:
        producer_names.setdefault(row.producer_id, row.producer_name)
        producer_mbids.setdefault(row.producer_id, row.producer_mbid)
        producer_types.setdefault(row.producer_id, row.producer_type)
        producer_countries.setdefault(row.producer_id, row.producer_country)
        album_roles.setdefault(row.album_id, set()).add("album")

    for producer_id in sorted(producer_names, key=str):
        nodes[artist_key(producer_id)] = _artist_node(
            artist_id=producer_id,
            label=producer_names[producer_id],
            mbid=producer_mbids[producer_id],
            artist_type=producer_types[producer_id],
            country=producer_countries[producer_id],
            roles=("producer",),
        )

    graph = nx.Graph()
    for node in nodes.values():
        graph.add_node(node.node_key, **_graph_node_attributes(node))

    edges: list[GraphEdgeSpec] = []
    for row in role_rows:
        source = artist_key(row.producer_id)
        target = album_key(row.album_id)
        edges.append(
            GraphEdgeSpec(
                layer_code=PRODUCER_ALBUM,
                source_key=source,
                target_key=target,
                role_code=row.role_code,
                weight=1.0,
                supporting_recordings=row.supporting_recordings,
                album_recordings=row.album_recordings,
                support_ratio=row.support_ratio,
                scope_mix=dict(row.scope_mix),
                evidence=dict(row.evidence),
            )
        )
        _add_simple_edge(
            graph,
            source,
            target,
            layer=PRODUCER_ALBUM,
            role=row.role_code,
            support_ratio=row.support_ratio,
        )

    edges.sort(key=lambda edge: (edge.layer_code, edge.source_key, edge.target_key, edge.role_code))
    ordered_nodes = tuple(nodes[key] for key in sorted(nodes))
    return ProducerAlbumLayer(graph=graph, nodes=ordered_nodes, edges=tuple(edges))


def _album_node(album: AlbumRow) -> GraphNodeSpec:
    year = album.first_release_date.year if album.first_release_date else None
    return GraphNodeSpec(
        node_key=album_key(album.album_id),
        node_type="album",
        entity_id=album.album_id,
        mbid=album.album_mbid,
        label=album.album_title,
        roles=("album",),
        attributes={
            "band_id": str(album.band_id),
            "band_name": album.band_name,
            "band_mbid": album.band_mbid,
            "band_type": album.band_type,
            "band_country": album.band_country,
            "year": year,
            "decade": _decade(album.first_release_date),
            "primary_code": album.primary_code,
            "primary_status": album.primary_status,
            "secondary_codes": list(album.secondary_codes),
        },
    )


def _artist_node(
    *,
    artist_id: uuid.UUID,
    label: str,
    mbid: str,
    artist_type: str,
    country: str | None,
    roles: tuple[str, ...],
) -> GraphNodeSpec:
    return GraphNodeSpec(
        node_key=artist_key(artist_id),
        node_type="artist",
        entity_id=artist_id,
        mbid=mbid,
        label=label,
        roles=roles,
        attributes={
            "artist_type": artist_type,
            "country": country,
        },
    )


def _graph_node_attributes(node: GraphNodeSpec) -> dict[str, Any]:
    return {
        "node_type": node.node_type,
        "entity_id": str(node.entity_id),
        "label": node.label,
        "mbid": node.mbid,
        "roles": node.roles,
        **node.attributes,
    }


def _add_simple_edge(
    graph: nx.Graph,
    source: str,
    target: str,
    *,
    layer: str,
    role: str,
    support_ratio: float | None,
) -> None:
    if graph.has_edge(source, target):
        edge = graph[source][target]
        roles = set(edge.get("roles", ()))
        roles.add(role)
        edge["roles"] = tuple(sorted(roles))
        edge["layer_codes"] = tuple(sorted(set(edge.get("layer_codes", ())) | {layer}))
        ratios = [
            value for value in (edge.get("support_ratio"), support_ratio) if value is not None
        ]
        edge["support_ratio"] = max(ratios) if ratios else None
        return
    graph.add_edge(
        source,
        target,
        roles=(role,),
        layer_codes=(layer,),
        support_ratio=support_ratio,
        weight=1.0,
    )


def _decade(value: date | None) -> str:
    if value is None:
        return "unknown"
    return f"{(value.year // 10) * 10}s"


@dataclass(frozen=True, slots=True)
class ProducerBandLayer:
    graph: nx.Graph
    nodes: tuple[GraphNodeSpec, ...]
    edges: tuple[GraphEdgeSpec, ...]
    self_produced_albums: dict[uuid.UUID, int]


def build_producer_band_layer(
    data: NetworkData,
    album_layer: ProducerAlbumLayer,
) -> ProducerBandLayer:
    nodes: dict[str, GraphNodeSpec] = {
        node.node_key: node for node in album_layer.nodes if node.node_type == "artist"
    }
    grouped: dict[tuple[uuid.UUID, uuid.UUID], list[Any]] = {}
    self_produced: dict[uuid.UUID, set[uuid.UUID]] = {}
    for row in data.producer_albums:
        album = data.albums[row.album_id]
        key = (row.producer_id, album.band_id)
        grouped.setdefault(key, []).append(row)
        if row.producer_id == album.band_id:
            self_produced.setdefault(row.producer_id, set()).add(row.album_id)

    band_metadata: dict[uuid.UUID, AlbumRow] = {}
    for row in data.producer_albums:
        band_metadata.setdefault(data.albums[row.album_id].band_id, data.albums[row.album_id])

    for band_id, album in sorted(band_metadata.items(), key=lambda item: str(item[0])):
        key = artist_key(band_id)
        existing = nodes.get(key)
        roles = set(existing.roles) if existing else set()
        roles.add("band")
        if band_id in self_produced:
            roles.add("producer")
        attributes = dict(existing.attributes) if existing else {}
        attributes.update(
            {
                "band_type": album.band_type,
                "band_country": album.band_country,
                "self_produced_albums": len(self_produced.get(band_id, set())),
            }
        )
        nodes[key] = GraphNodeSpec(
            node_key=key,
            node_type="artist",
            entity_id=band_id,
            mbid=album.band_mbid,
            label=album.band_name,
            roles=tuple(sorted(roles)),
            attributes=attributes,
        )

    graph = nx.Graph()
    for node in nodes.values():
        graph.add_node(node.node_key, **_graph_node_attributes(node))

    edges: list[GraphEdgeSpec] = []
    for (producer_id, band_id), rows in sorted(
        grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
    ):
        if producer_id == band_id:
            continue
        album_rows: dict[uuid.UUID, list[Any]] = {}
        for row in rows:
            album_rows.setdefault(row.album_id, []).append(row)
        album_ids = sorted(album_rows, key=str)
        years = sorted(
            album.first_release_date.year
            for album_id in album_ids
            if (album := data.albums[album_id]).first_release_date is not None
        )
        role_mix: dict[str, int] = {}
        full = 0
        partial = 0
        unknown = 0
        for album_id in album_ids:
            ratios = [row.support_ratio for row in album_rows[album_id]]
            if any(ratio == 1.0 for ratio in ratios):
                full += 1
            elif any(ratio is not None for ratio in ratios):
                partial += 1
            else:
                unknown += 1
            for row in album_rows[album_id]:
                role_mix[row.role_code] = role_mix.get(row.role_code, 0) + 1
        source = artist_key(producer_id)
        target = artist_key(band_id)
        edges.append(
            GraphEdgeSpec(
                layer_code=PRODUCER_BAND,
                source_key=source,
                target_key=target,
                role_code="mixed",
                weight=float(len(album_ids)),
                supporting_recordings=None,
                album_recordings=None,
                support_ratio=None,
                scope_mix={},
                evidence={
                    "album_count": len(album_ids),
                    "album_ids": [str(album_id) for album_id in album_ids],
                    "album_titles": [data.albums[album_id].album_title for album_id in album_ids],
                    "first_year": years[0] if years else None,
                    "last_year": years[-1] if years else None,
                    "role_mix": dict(sorted(role_mix.items())),
                    "support": {"full": full, "partial": partial, "unknown": unknown},
                },
            )
        )
        graph.add_edge(
            source,
            target,
            layer_codes=(PRODUCER_BAND,),
            weight=float(len(album_ids)),
            album_count=len(album_ids),
            first_year=years[0] if years else None,
            last_year=years[-1] if years else None,
        )

    edges.sort(key=lambda edge: (edge.layer_code, edge.source_key, edge.target_key))
    ordered_nodes = tuple(nodes[key] for key in sorted(nodes))
    self_counts = {key: len(value) for key, value in sorted(self_produced.items())}
    return ProducerBandLayer(
        graph=graph,
        nodes=ordered_nodes,
        edges=tuple(edges),
        self_produced_albums=self_counts,
    )
