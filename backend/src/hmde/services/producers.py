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
    ProducerOverviewGraphLayout,
    ProducerOverviewGraphLayoutNode,
    ProducerOverviewGraphLimits,
    ProducerOverviewGraphMeta,
    ProducerOverviewGraphResponse,
)
from hmde.services.graph_layouts import (
    compute_bipartite_layout,
    compute_community_layout,
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


def get_producer_overview_graph(
    session: Session,
    run: AnalysisRun,
    *,
    view: str,
    producer_limit: int,
    producer_sort: str,
    order: str,
    decade: str | None,
    subgenre: str | None,
    include_isolated: bool,
    include_evidence: bool,
    max_nodes: int,
    max_edges: int,
    layout: str | None = None,
) -> ProducerOverviewGraphResponse:
    all_nodes = {
        node.id: node
        for node in session.scalars(select(GraphNode).where(GraphNode.analysis_run_id == run.id))
    }
    nodes_by_entity = {
        node.entity_id: node
        for node in all_nodes.values()
        if node.node_type == "artist" and _is_producer_node(node)
    }
    ranking, matched = list_producers(
        session,
        run,
        q=None,
        decade=decade,
        subgenre=subgenre,
        sort=producer_sort,
        order=order,
        limit=1_000_000,
        offset=0,
    )
    selected_rows = ranking[:producer_limit] if producer_limit else ranking
    producer_rows = {item.id: item for item in selected_rows if item.id in nodes_by_entity}
    producer_order = [
        nodes_by_entity[item.id].id for item in selected_rows if item.id in producer_rows
    ]
    producer_ids = set(producer_order)

    layer = PRODUCER_ALBUM if view == "albums" else PRODUCER_BAND
    edge_rows: list[GraphEdge] = []
    if producer_ids:
        edge_rows = list(
            session.scalars(
                select(GraphEdge).where(
                    GraphEdge.analysis_run_id == run.id,
                    GraphEdge.layer_code == layer,
                    GraphEdge.source_node_id.in_(producer_ids),
                )
            )
        )

    filtered_edges: list[GraphEdge] = []
    for edge in edge_rows:
        target = all_nodes.get(edge.target_node_id)
        if target is None:
            continue
        if view == "albums":
            attributes = target.attributes if isinstance(target.attributes, dict) else {}
            if decade and attributes.get("decade") != decade:
                continue
            if subgenre and attributes.get("primary_code") != subgenre:
                continue
        filtered_edges.append(edge)

    grouped: dict[tuple[UUID, UUID], list[GraphEdge]] = defaultdict(list)
    for edge in filtered_edges:
        grouped[(edge.source_node_id, edge.target_node_id)].append(edge)

    if not include_isolated:
        connected = {source_id for source_id, _ in grouped}
        producer_order = [node_id for node_id in producer_order if node_id in connected]

    truncated = matched > len(selected_rows)
    if len(producer_order) > max_nodes:
        producer_order = producer_order[:max_nodes]
        truncated = True
    selected_nodes = set(producer_order)

    merged_edges: list[tuple[GraphEdge, list[str]]] = []
    for rows in grouped.values():
        source_id = rows[0].source_node_id
        if source_id not in selected_nodes:
            continue
        best = max(
            rows,
            key=lambda item: (
                item.support_ratio if item.support_ratio is not None else -1.0,
                item.weight,
                str(item.id),
            ),
        )
        merged_edges.append((best, sorted({item.role_code for item in rows})))
    merged_edges.sort(
        key=lambda item: (
            -item[0].weight,
            str(all_nodes[item[0].source_node_id].entity_id),
            str(all_nodes[item[0].target_node_id].entity_id),
        )
    )

    selected_edges: list[GraphEdge] = []
    edge_roles: dict[UUID, list[str]] = {}
    selected_producer_ids = set(producer_order)
    for edge, roles in merged_edges:
        if len(selected_edges) >= max_edges:
            truncated = True
            break
        if edge.target_node_id not in selected_nodes:
            if len(selected_nodes) >= max_nodes:
                truncated = True
                continue
            selected_nodes.add(edge.target_node_id)
        selected_edges.append(edge)
        edge_roles[edge.id] = roles

    target_ids = {edge.target_node_id for edge in selected_edges}
    edge_source_ids = {edge.source_node_id for edge in selected_edges}
    node_payload = [
        _overview_node_payload(
            all_nodes[node_id],
            view=view,
            producer_row=producer_rows.get(all_nodes[node_id].entity_id),
            display_type=(
                "band"
                if view == "bands" and node_id in target_ids and node_id not in edge_source_ids
                else None
            ),
        )
        for node_id in sorted(selected_nodes, key=str)
        if node_id in all_nodes
    ]
    edge_payload = [
        _overview_edge_payload(
            edge,
            nodes_by_id=all_nodes,
            roles=edge_roles[edge.id],
            include_evidence=include_evidence,
        )
        for edge in selected_edges
    ]
    layout_payload = _overview_layout_payload(
        session,
        run,
        layout=layout,
        selected_nodes=selected_nodes,
        selected_producer_ids=selected_producer_ids,
        selected_edges=selected_edges,
        all_nodes=all_nodes,
    )
    meta = ProducerOverviewGraphMeta(
        scope="overview",
        view=view,
        analysis_run_id=run.id,
        analysis_version=run.analysis_version,
        dataset_version=run.dataset_version,
        taxonomy_version=run.taxonomy_version,
        graph_version=run.graph_version,
        truncated=truncated,
        matched_producers=matched,
        selected_producers=sum(1 for node_id in selected_nodes if node_id in selected_producer_ids),
        include_isolated=include_isolated,
        limits=ProducerOverviewGraphLimits(
            producer_limit=producer_limit,
            max_nodes=max_nodes,
            max_edges=max_edges,
        ),
    )
    return ProducerOverviewGraphResponse(
        nodes=node_payload,
        edges=edge_payload,
        meta=meta,
        layout=layout_payload,
    )


def _overview_layout_payload(
    session: Session,
    run: AnalysisRun,
    *,
    layout: str | None,
    selected_nodes: set[UUID],
    selected_producer_ids: set[UUID],
    selected_edges: list[GraphEdge],
    all_nodes: dict[UUID, GraphNode],
) -> ProducerOverviewGraphLayout | None:
    if layout is None:
        return None
    try:
        node_ids = [
            all_nodes[node_id].entity_id for node_id in selected_nodes if node_id in all_nodes
        ]
        producer_ids = {
            all_nodes[node_id].entity_id
            for node_id in selected_producer_ids
            if node_id in all_nodes
        }
        edges = [
            (
                all_nodes[edge.source_node_id].entity_id,
                all_nodes[edge.target_node_id].entity_id,
            )
            for edge in selected_edges
        ]
        if layout == "community":
            community_by_node = _community_map(session, run=run)
            positions = compute_community_layout(
                node_ids,
                producer_ids,
                edges,
                {
                    all_nodes[node_id].entity_id: community_by_node.get(node_id, "unassigned")
                    for node_id in selected_producer_ids
                    if node_id in all_nodes
                },
            )
        else:
            positions = compute_bipartite_layout(node_ids, producer_ids, edges)
        return ProducerOverviewGraphLayout(
            algorithm=layout,
            nodes=[
                ProducerOverviewGraphLayoutNode(
                    id=node_id,
                    x=positions[node_id][0],
                    y=positions[node_id][1],
                )
                for node_id in sorted(positions, key=str)
            ],
        )
    except Exception:
        return None


def _overview_node_payload(
    node: GraphNode,
    *,
    view: str,
    producer_row: ProducerListItem | None,
    display_type: str | None,
) -> ProducerGraphNode:
    payload = _node_payload(node, view=view)
    if producer_row is not None and "producer" in node.roles:
        attributes = dict(payload.attributes)
        attributes.update(
            {
                "album_count": producer_row.album_count,
                "band_count": producer_row.band_count,
                "betweenness": producer_row.betweenness,
                "community_key": producer_row.community_key,
            }
        )
        payload = payload.model_copy(update={"attributes": attributes})
    if display_type is not None and payload.type != display_type:
        payload = payload.model_copy(update={"type": display_type})
    return payload


def _overview_edge_payload(
    edge: GraphEdge,
    *,
    nodes_by_id: dict[UUID, GraphNode],
    roles: list[str],
    include_evidence: bool,
) -> ProducerGraphEdge:
    source = nodes_by_id[edge.source_node_id]
    target = nodes_by_id[edge.target_node_id]
    evidence = dict(edge.evidence) if include_evidence else {}
    if include_evidence and len(roles) > 1:
        evidence["roles"] = roles
    return ProducerGraphEdge(
        source=source.entity_id,
        target=target.entity_id,
        layer=edge.layer_code,
        role=roles[0] if len(roles) == 1 else "mixed",
        weight=edge.weight,
        support_ratio=edge.support_ratio,
        supporting_recordings=edge.supporting_recordings,
        album_recordings=edge.album_recordings,
        album_count=edge.evidence.get("album_count") if isinstance(edge.evidence, dict) else None,
        evidence=evidence,
    )


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
