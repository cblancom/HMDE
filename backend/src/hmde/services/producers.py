"""Producer ranking, detail and bounded graph services."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from hmde.models import (
    AnalysisRun,
    Community,
    CommunityMembership,
    GraphEdge,
    GraphNode,
    ProducerMetric,
)
from hmde.schemas.api import (
    AnalysisRunMeta,
    ProducerAlbumSummary,
    ProducerBandSummary,
    ProducerDetailResponse,
    ProducerGraphEdge,
    ProducerGraphLimits,
    ProducerGraphMeta,
    ProducerGraphNode,
    ProducerGraphResponse,
    ProducerListItem,
)

PRODUCER_ALBUM = "producer_album"
PRODUCER_BAND = "producer_band"


def run_meta(run: AnalysisRun) -> AnalysisRunMeta:
    return AnalysisRunMeta(
        analysis_run_id=run.id,
        analysis_version=run.analysis_version,
        dataset_version=run.dataset_version,
        taxonomy_version=run.taxonomy_version,
        graph_version=run.graph_version,
        finished_at=run.finished_at,
    )


def list_producers(
    session: Session,
    run: AnalysisRun,
    *,
    q: str | None,
    decade: str | None,
    subgenre: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> tuple[list[ProducerListItem], int]:
    nodes = list(
        session.scalars(
            select(GraphNode).where(
                GraphNode.analysis_run_id == run.id,
                GraphNode.node_type == "artist",
            )
        )
    )
    producer_nodes = [node for node in nodes if "producer" in node.roles]
    if q:
        query = q.casefold()
        producer_nodes = [node for node in producer_nodes if query in node.label.casefold()]
    if decade or subgenre:
        matching = _producer_nodes_matching_filters(
            session, run=run, decade=decade, subgenre=subgenre
        )
        producer_nodes = [node for node in producer_nodes if node.id in matching]

    metrics = _producer_metrics(session, run=run)
    communities = _community_map(session, run=run)
    rows = [
        ProducerListItem(
            id=node.entity_id,
            mbid=node.mbid or "",
            name=node.label,
            country=node.attributes.get("country"),
            artist_type=str(node.attributes.get("artist_type") or "other"),
            album_count=int(metrics.get(node.id, {}).get("NA-PROD-001", 0)),
            band_count=int(metrics.get(node.id, {}).get("NA-PROD-002", 0)),
            self_produced_albums=int(metrics.get(node.id, {}).get("NA-PROD-003", 0)),
            betweenness=metrics.get(node.id, {}).get("NA-BET-001"),
            community_key=communities.get(node.id),
        )
        for node in producer_nodes
    ]
    reverse = order == "desc"
    if sort == "name":
        rows.sort(key=lambda row: (row.name.casefold(), str(row.id)), reverse=reverse)
    else:
        key = {
            "album_count": "album_count",
            "band_count": "band_count",
            "betweenness": "betweenness",
        }[sort]
        rows.sort(
            key=lambda row: (
                getattr(row, key) if getattr(row, key) is not None else -1.0,
                row.name.casefold(),
                str(row.id),
            ),
            reverse=reverse,
        )
    total = len(rows)
    return rows[offset : offset + limit], total


def get_producer_detail(
    session: Session,
    run: AnalysisRun,
    producer_id: UUID,
    *,
    limit: int = 20,
) -> ProducerDetailResponse | None:
    node = _producer_node(session, run=run, producer_id=producer_id)
    if node is None:
        return None
    metrics = _producer_metrics(session, run=run)
    producer_metrics = metrics.get(node.id, {})
    communities = _community_map(session, run=run)
    albums = _top_albums(session, run=run, node=node, limit=limit)
    bands = _top_bands(session, run=run, node=node, limit=limit)
    return ProducerDetailResponse(
        id=node.entity_id,
        mbid=node.mbid or "",
        name=node.label,
        country=node.attributes.get("country"),
        artist_type=str(node.attributes.get("artist_type") or "other"),
        album_count=int(producer_metrics.get("NA-PROD-001", 0)),
        band_count=int(producer_metrics.get("NA-PROD-002", 0)),
        self_produced_albums=int(producer_metrics.get("NA-PROD-003", 0)),
        betweenness=producer_metrics.get("NA-BET-001"),
        community_key=communities.get(node.id),
        top_albums=albums,
        top_bands=bands,
        meta=run_meta(run),
    )


def get_producer_graph(
    session: Session,
    run: AnalysisRun,
    producer_id: UUID,
    *,
    view: str,
    limit: int,
    depth: int,
    max_nodes: int,
    max_edges: int,
    include_evidence: bool,
) -> ProducerGraphResponse | None:
    start = _producer_node(session, run=run, producer_id=producer_id)
    if start is None:
        return None
    layer = PRODUCER_ALBUM if view == "albums" else PRODUCER_BAND
    all_nodes = {
        node.id: node
        for node in session.scalars(select(GraphNode).where(GraphNode.analysis_run_id == run.id))
    }
    selected_nodes = {start.id}
    selected_edges: dict[UUID, GraphEdge] = {}
    frontier = {start.id}
    truncated = False
    for level in range(depth):
        if not frontier:
            break
        edge_rows = list(
            session.scalars(
                select(GraphEdge)
                .where(
                    GraphEdge.analysis_run_id == run.id,
                    GraphEdge.layer_code == layer,
                    or_(
                        GraphEdge.source_node_id.in_(frontier),
                        GraphEdge.target_node_id.in_(frontier),
                    ),
                )
                .order_by(
                    GraphEdge.weight.desc(),
                    GraphEdge.source_node_id,
                    GraphEdge.target_node_id,
                )
            )
        )
        if len(edge_rows) > limit:
            edge_rows = edge_rows[:limit]
            truncated = True
        next_frontier: set[UUID] = set()
        for edge in edge_rows:
            if len(selected_edges) >= max_edges:
                truncated = True
                break
            other = edge.target_node_id if edge.source_node_id in frontier else edge.source_node_id
            if other not in selected_nodes and len(selected_nodes) >= max_nodes:
                truncated = True
                continue
            selected_nodes.add(other)
            selected_edges[edge.id] = edge
            next_frontier.add(other)
        frontier = next_frontier
        if level + 1 < depth and len(edge_rows) >= limit:
            truncated = True

    node_payload = [
        _node_payload(all_nodes[node_id], view=view)
        for node_id in sorted(selected_nodes, key=str)
        if node_id in all_nodes
    ]
    edge_payload = [
        _edge_payload(edge, nodes_by_id=all_nodes, include_evidence=include_evidence)
        for edge in sorted(
            selected_edges.values(),
            key=lambda item: (item.source_node_id, item.target_node_id, str(item.id)),
        )
    ]
    meta = ProducerGraphMeta(
        view=view,
        analysis_run_id=run.id,
        analysis_version=run.analysis_version,
        dataset_version=run.dataset_version,
        taxonomy_version=run.taxonomy_version,
        graph_version=run.graph_version,
        truncated=truncated,
        limits=ProducerGraphLimits(
            limit=limit,
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        ),
    )
    return ProducerGraphResponse(nodes=node_payload, edges=edge_payload, meta=meta)


def _producer_node(session: Session, *, run: AnalysisRun, producer_id: UUID) -> GraphNode | None:
    node = session.scalar(
        select(GraphNode).where(
            GraphNode.analysis_run_id == run.id,
            GraphNode.entity_id == producer_id,
            GraphNode.node_type == "artist",
        )
    )
    return node if _is_producer_node(node) else None


def _is_producer_node(node: GraphNode | None) -> bool:
    return node is not None and "producer" in node.roles


def _producer_metrics(session: Session, *, run: AnalysisRun) -> dict[UUID, dict[str, float]]:
    rows = session.scalars(select(ProducerMetric).where(ProducerMetric.analysis_run_id == run.id))
    result: dict[UUID, dict[str, float]] = defaultdict(dict)
    for row in rows:
        result[row.producer_node_id][row.metric_code] = row.value
    return result


def _community_map(session: Session, *, run: AnalysisRun) -> dict[UUID, str]:
    rows = session.execute(
        select(CommunityMembership.node_id, Community.community_key)
        .join(Community, Community.id == CommunityMembership.community_id)
        .where(CommunityMembership.analysis_run_id == run.id)
    ).all()
    return {node_id: community_key for node_id, community_key in rows}


def _producer_nodes_matching_filters(
    session: Session,
    *,
    run: AnalysisRun,
    decade: str | None,
    subgenre: str | None,
) -> set[UUID]:
    target = GraphNode.__table__.alias("target")
    conditions = [
        GraphEdge.analysis_run_id == run.id,
        GraphEdge.layer_code == PRODUCER_ALBUM,
        target.c.id == GraphEdge.target_node_id,
    ]
    if decade:
        conditions.append(target.c.attributes["decade"].astext == decade)
    if subgenre:
        conditions.append(target.c.attributes["primary_code"].astext == subgenre)
    rows = session.execute(
        select(GraphEdge.source_node_id)
        .select_from(GraphEdge)
        .join(target, target.c.id == GraphEdge.target_node_id)
        .where(*conditions)
        .distinct()
    ).scalars()
    return set(rows)


def _top_albums(
    session: Session, *, run: AnalysisRun, node: GraphNode, limit: int
) -> list[ProducerAlbumSummary]:
    target = GraphNode.__table__.alias("album_target")
    rows = session.execute(
        select(GraphEdge, target.c.entity_id, target.c.label, target.c.attributes)
        .select_from(GraphEdge)
        .join(target, target.c.id == GraphEdge.target_node_id)
        .where(
            GraphEdge.analysis_run_id == run.id,
            GraphEdge.layer_code == PRODUCER_ALBUM,
            GraphEdge.source_node_id == node.id,
        )
        .order_by(GraphEdge.support_ratio.desc().nullslast(), target.c.label)
        .limit(limit)
    ).all()
    return [
        ProducerAlbumSummary(
            album_id=album_id,
            title=str(label),
            band_name=str(attributes.get("band_name") if isinstance(attributes, dict) else ""),
            year=attributes.get("year") if isinstance(attributes, dict) else None,
            role=edge.role_code,
            support_ratio=edge.support_ratio,
        )
        for edge, album_id, label, attributes in rows
    ]


def _top_bands(
    session: Session, *, run: AnalysisRun, node: GraphNode, limit: int
) -> list[ProducerBandSummary]:
    target = GraphNode.__table__.alias("band_target")
    rows = session.execute(
        select(GraphEdge, target.c.entity_id, target.c.label)
        .select_from(GraphEdge)
        .join(target, target.c.id == GraphEdge.target_node_id)
        .where(
            GraphEdge.analysis_run_id == run.id,
            GraphEdge.layer_code == PRODUCER_BAND,
            GraphEdge.source_node_id == node.id,
        )
        .order_by(GraphEdge.weight.desc(), target.c.label)
        .limit(limit)
    ).all()
    return [
        ProducerBandSummary(
            band_id=band_id,
            name=str(label),
            album_count=int(edge.evidence.get("album_count", 0)),
            first_year=edge.evidence.get("first_year"),
            last_year=edge.evidence.get("last_year"),
        )
        for edge, band_id, label in rows
    ]


def _node_payload(node: GraphNode, *, view: str) -> ProducerGraphNode:
    roles = set(node.roles)
    if node.node_type == "album":
        node_type = "album"
    elif "producer" in roles:
        node_type = "producer"
    else:
        node_type = "band"
    return ProducerGraphNode(
        id=node.entity_id,
        type=node_type,
        label=node.label,
        roles=list(node.roles),
        attributes=dict(node.attributes),
    )


def _edge_payload(
    edge: GraphEdge,
    *,
    nodes_by_id: dict[UUID, GraphNode],
    include_evidence: bool,
) -> ProducerGraphEdge:
    source = nodes_by_id[edge.source_node_id]
    target = nodes_by_id[edge.target_node_id]
    evidence = dict(edge.evidence) if include_evidence else {}
    return ProducerGraphEdge(
        source=source.entity_id,
        target=target.entity_id,
        layer=edge.layer_code,
        role=edge.role_code,
        weight=edge.weight,
        support_ratio=edge.support_ratio,
        supporting_recordings=edge.supporting_recordings,
        album_recordings=edge.album_recordings,
        album_count=edge.evidence.get("album_count") if isinstance(edge.evidence, dict) else None,
        evidence=evidence,
    )
