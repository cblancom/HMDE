"""Analysis-run, summary, temporal and community read services."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hmde.models import (
    AnalysisRun,
    Community,
    CommunityMembership,
    GraphNode,
    ProducerMetric,
    TemporalMetric,
)
from hmde.schemas.api import (
    AnalysisRunListItem,
    AnalyticsSummaryResponse,
    CommunityDetailResponse,
    CommunityListItem,
    CommunityMember,
    DecadeMetricItem,
)
from hmde.services.producers import run_meta


def list_analysis_runs(
    session: Session,
    *,
    limit: int,
    offset: int,
) -> tuple[list[AnalysisRunListItem], int]:
    statement = (
        select(AnalysisRun)
        .order_by(AnalysisRun.started_at.desc(), AnalysisRun.id)
        .limit(limit)
        .offset(offset)
    )
    total = session.scalar(select(func.count(AnalysisRun.id))) or 0
    return [_run_item(run) for run in session.scalars(statement)], int(total)


def get_analysis_run_item(session: Session, run_id: UUID) -> AnalysisRunListItem | None:
    run = session.get(AnalysisRun, run_id)
    return _run_item(run) if run else None


def get_summary(session: Session, run: AnalysisRun) -> AnalyticsSummaryResponse:
    counters = run.counters or {}
    top_albums = _top_producer_metrics(session, run=run, code="NA-PROD-001")
    top_bands = _top_producer_metrics(session, run=run, code="NA-PROD-002")
    community_count = int(
        session.scalar(select(func.count(Community.id)).where(Community.analysis_run_id == run.id))
        or 0
    )
    return AnalyticsSummaryResponse(
        graph_counts=counters.get("graphs", {}),
        support=counters.get("support", {}),
        top_albums=top_albums,
        top_bands=top_bands,
        community_count=community_count,
        meta=run_meta(run),
    )


def get_decades(session: Session, run: AnalysisRun) -> list[DecadeMetricItem]:
    rows = session.scalars(
        select(TemporalMetric)
        .where(
            TemporalMetric.analysis_run_id == run.id,
            TemporalMetric.scope_type == "decade",
        )
        .order_by(TemporalMetric.layer_code, TemporalMetric.scope_key, TemporalMetric.metric_code)
    )
    return [
        DecadeMetricItem(
            layer_code=row.layer_code,
            scope_key=row.scope_key,
            metric_code=row.metric_code,
            numerator=row.numerator,
            denominator=row.denominator,
            value=row.value,
            unit=row.unit,
        )
        for row in rows
    ]


def list_communities(
    session: Session,
    run: AnalysisRun,
    *,
    limit: int,
    offset: int,
) -> tuple[list[CommunityListItem], int]:
    statement = (
        select(Community)
        .where(Community.analysis_run_id == run.id)
        .order_by(Community.community_key)
        .limit(limit)
        .offset(offset)
    )
    total = (
        session.scalar(select(func.count(Community.id)).where(Community.analysis_run_id == run.id))
        or 0
    )
    items = [
        CommunityListItem(
            community_key=row.community_key,
            algorithm=row.algorithm,
            resolution=row.resolution,
            size=row.size,
        )
        for row in session.scalars(statement)
    ]
    return items, int(total)


def get_community(
    session: Session,
    run: AnalysisRun,
    community_key: str,
) -> CommunityDetailResponse | None:
    community = session.scalar(
        select(Community).where(
            Community.analysis_run_id == run.id,
            Community.community_key == community_key,
        )
    )
    if community is None:
        return None
    rows = session.execute(
        select(GraphNode)
        .join(CommunityMembership, CommunityMembership.node_id == GraphNode.id)
        .where(
            CommunityMembership.analysis_run_id == run.id,
            CommunityMembership.community_id == community.id,
        )
        .order_by(GraphNode.label, GraphNode.id)
    ).scalars()
    return CommunityDetailResponse(
        community_key=community.community_key,
        algorithm=community.algorithm,
        resolution=community.resolution,
        size=community.size,
        members=[CommunityMember(producer_id=node.entity_id, name=node.label) for node in rows],
        meta=run_meta(run),
    )


def _run_item(run: AnalysisRun) -> AnalysisRunListItem:
    return AnalysisRunListItem(
        **run_meta(run).model_dump(),
        status=run.status,
        code_version=run.code_version,
        started_at=run.started_at,
        report_path=run.report_path,
    )


def _top_producer_metrics(
    session: Session,
    *,
    run: AnalysisRun,
    code: str,
) -> list[dict[str, object]]:
    rows = session.execute(
        select(ProducerMetric, GraphNode)
        .join(GraphNode, GraphNode.id == ProducerMetric.producer_node_id)
        .where(
            ProducerMetric.analysis_run_id == run.id,
            ProducerMetric.metric_code == code,
        )
        .order_by(ProducerMetric.value.desc(), GraphNode.label, GraphNode.id)
        .limit(20)
    ).all()
    return [
        {
            "producer_id": str(node.entity_id),
            "producer": node.label,
            "count": metric.value,
        }
        for metric, node in rows
    ]
