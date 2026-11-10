"""Analytical run lifecycle and graph persistence."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import (
    AnalysisRun,
    Community,
    CommunityMembership,
    GraphEdge,
    GraphNode,
    NodeMetric,
    ProducerMetric,
    TemporalMetric,
)

from .graph import (
    GraphEdgeSpec,
    GraphNodeSpec,
    ProducerAlbumLayer,
    ProducerBandLayer,
    artist_key,
)
from .inputs import NetworkInputs
from .loader import NetworkData
from .metrics import MetricsPayload


def analysis_version(
    inputs: NetworkInputs,
    *,
    graph_version: str,
    code_version: str,
    parameters: dict[str, Any],
) -> str:
    context = {
        "dataset_version": inputs.normalization_run.dataset_version,
        "normalization_run_id": str(inputs.normalization_run.id),
        "quality_run_id": str(inputs.quality_run.id),
        "taxonomy_version": inputs.taxonomy_version,
        "graph_version": graph_version,
        "code_version": code_version,
        "parameters": parameters,
    }
    digest = hashlib.sha256(
        json.dumps(context, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return f"net-{digest[:16]}"


def find_completed_run(session: Session, *, version: str) -> AnalysisRun | None:
    return session.scalar(
        select(AnalysisRun)
        .where(
            AnalysisRun.analysis_version == version,
            AnalysisRun.status.in_(("completed", "completed_with_limitations")),
        )
        .order_by(AnalysisRun.started_at.desc())
        .limit(1)
    )


def start_analysis_run(
    session: Session,
    *,
    version: str,
    inputs: NetworkInputs,
    graph_version: str,
    code_version: str,
    parameters: dict[str, Any],
) -> AnalysisRun:
    run = AnalysisRun(
        id=uuid.uuid4(),
        analysis_version=version,
        normalization_run_id=inputs.normalization_run.id,
        quality_run_id=inputs.quality_run.id,
        dataset_version=inputs.normalization_run.dataset_version or "",
        taxonomy_version=inputs.taxonomy_version,
        graph_version=graph_version,
        code_version=code_version,
        status="running",
        parameters=parameters,
        counters={},
    )
    session.add(run)
    session.flush()
    return run


def persist_network_run(
    session: Session,
    *,
    run: AnalysisRun,
    data: NetworkData,
    album_layer: ProducerAlbumLayer,
    band_layer: ProducerBandLayer,
    metrics: MetricsPayload,
    report_path: str | None = None,
) -> AnalysisRun:
    nodes = _merged_nodes(album_layer, band_layer)
    node_rows = _persist_nodes(session, run=run, nodes=nodes)
    _persist_edges(
        session,
        run=run,
        node_rows=node_rows,
        edges=(*album_layer.edges, *band_layer.edges),
    )
    _persist_node_metrics(
        session,
        run=run,
        node_rows=node_rows,
        metrics=metrics.node_metrics,
    )
    _persist_producer_metrics(
        session,
        run=run,
        node_rows=node_rows,
        metrics=metrics.producer_metrics,
    )
    _persist_temporal_metrics(session, run=run, metrics=metrics.temporal_metrics)
    _persist_communities(
        session,
        run=run,
        node_rows=node_rows,
        metrics=metrics.communities,
    )
    limitation = _has_limitations(data, metrics)
    counters = {
        "graphs": metrics.graph_counts,
        "support": metrics.support_summary,
        "communities": len(metrics.communities),
        "quality": asdict(data.quality),
        "advisories": list(metrics.advisories),
        "source": {
            "albums": len(data.albums),
            "producer_album_roles": len(data.producer_albums),
            "self_produced_albums": sum(
                1 for values in band_layer.self_produced_albums.values() for _ in range(values)
            ),
        },
    }
    run.counters = counters
    run.status = "completed_with_limitations" if limitation else "completed"
    run.finished_at = datetime.now(UTC)
    run.report_path = report_path
    session.flush()
    return run


def _merged_nodes(
    album_layer: ProducerAlbumLayer,
    band_layer: ProducerBandLayer,
) -> tuple[GraphNodeSpec, ...]:
    nodes = {node.node_key: node for node in album_layer.nodes}
    for node in band_layer.nodes:
        existing = nodes.get(node.node_key)
        if existing is None:
            nodes[node.node_key] = node
            continue
        roles = tuple(sorted(set(existing.roles) | set(node.roles)))
        attributes = {**existing.attributes, **node.attributes}
        nodes[node.node_key] = GraphNodeSpec(
            node_key=node.node_key,
            node_type=node.node_type,
            entity_id=node.entity_id,
            mbid=node.mbid or existing.mbid,
            label=node.label or existing.label,
            roles=roles,
            attributes=attributes,
        )
    return tuple(nodes[key] for key in sorted(nodes))


def _persist_nodes(
    session: Session,
    *,
    run: AnalysisRun,
    nodes: tuple[GraphNodeSpec, ...],
) -> dict[str, GraphNode]:
    rows: dict[str, GraphNode] = {}
    for node in nodes:
        row = GraphNode(
            id=uuid.uuid4(),
            analysis_run_id=run.id,
            node_key=node.node_key,
            node_type=node.node_type,
            entity_id=node.entity_id,
            mbid=node.mbid,
            label=node.label,
            roles=list(node.roles),
            attributes=node.attributes,
        )
        session.add(row)
        rows[node.node_key] = row
    session.flush()
    return rows


def _persist_edges(
    session: Session,
    *,
    run: AnalysisRun,
    node_rows: dict[str, GraphNode],
    edges: tuple[GraphEdgeSpec, ...],
) -> None:
    seen: set[tuple[str, str, str, str]] = set()
    for edge in edges:
        key = (edge.layer_code, edge.source_key, edge.target_key, edge.role_code)
        if key in seen:
            raise ValueError(f"duplicate graph edge: {key}")
        seen.add(key)
        if edge.source_key == edge.target_key:
            continue
        session.add(
            GraphEdge(
                id=uuid.uuid4(),
                analysis_run_id=run.id,
                layer_code=edge.layer_code,
                source_node_id=node_rows[edge.source_key].id,
                target_node_id=node_rows[edge.target_key].id,
                role_code=edge.role_code,
                weight=edge.weight,
                supporting_recordings=edge.supporting_recordings,
                album_recordings=edge.album_recordings,
                support_ratio=edge.support_ratio,
                scope_mix=edge.scope_mix,
                evidence=edge.evidence,
            )
        )
    session.flush()


def _persist_node_metrics(
    session: Session,
    *,
    run: AnalysisRun,
    node_rows: dict[str, GraphNode],
    metrics: tuple[Any, ...],
) -> None:
    for metric in metrics:
        session.add(
            NodeMetric(
                id=uuid.uuid4(),
                analysis_run_id=run.id,
                node_id=node_rows[metric.node_key].id,
                layer_code=metric.layer_code,
                metric_code=metric.metric_code,
                value=metric.value,
                numerator=metric.numerator,
                denominator=metric.denominator,
                unit=metric.unit,
                details=metric.details,
            )
        )
    session.flush()


def _persist_producer_metrics(
    session: Session,
    *,
    run: AnalysisRun,
    node_rows: dict[str, GraphNode],
    metrics: tuple[Any, ...],
) -> None:
    for metric in metrics:
        node_key = artist_key(metric.producer_id)
        if node_key not in node_rows:
            continue
        session.add(
            ProducerMetric(
                id=uuid.uuid4(),
                analysis_run_id=run.id,
                producer_node_id=node_rows[node_key].id,
                metric_code=metric.metric_code,
                value=metric.value,
                numerator=metric.numerator,
                denominator=metric.denominator,
                unit=metric.unit,
                details=metric.details,
            )
        )
    session.flush()


def _persist_temporal_metrics(
    session: Session,
    *,
    run: AnalysisRun,
    metrics: tuple[Any, ...],
) -> None:
    for metric in metrics:
        session.add(
            TemporalMetric(
                id=uuid.uuid4(),
                analysis_run_id=run.id,
                layer_code=metric.layer_code,
                scope_type=metric.scope_type,
                scope_key=metric.scope_key,
                metric_code=metric.metric_code,
                numerator=metric.numerator,
                denominator=metric.denominator,
                value=metric.value,
                unit=metric.unit,
                details=metric.details,
            )
        )
    session.flush()


def _persist_communities(
    session: Session,
    *,
    run: AnalysisRun,
    node_rows: dict[str, GraphNode],
    metrics: tuple[Any, ...],
) -> None:
    for community in metrics:
        row = Community(
            id=uuid.uuid4(),
            analysis_run_id=run.id,
            community_key=community.community_key,
            algorithm=community.algorithm,
            resolution=community.resolution,
            size=community.size,
            details=community.details,
        )
        session.add(row)
        session.flush()
        for node_key in community.member_keys:
            session.add(
                CommunityMembership(
                    id=uuid.uuid4(),
                    analysis_run_id=run.id,
                    community_id=row.id,
                    node_id=node_rows[node_key].id,
                )
            )
    session.flush()


def _has_limitations(data: NetworkData, metrics: MetricsPayload) -> bool:
    quality = data.quality
    return bool(
        metrics.advisories
        or metrics.support_summary.get("unknown", 0)
        or quality.findings
        or quality.missing_dates
        or quality.unclassified_albums
        or quality.duplicate_labels
    )
