"""Analysis-run, analytics and community API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from hmde.api.dependencies import get_analysis_run
from hmde.api.pagination import Pagination, pagination
from hmde.db.session import get_db
from hmde.models import AnalysisRun
from hmde.schemas.api import (
    AnalysisRunListItem,
    AnalysisRunListResponse,
    AnalyticsSummaryResponse,
    CommunityDetailResponse,
    CommunityListResponse,
    DecadeMetricResponse,
)
from hmde.services.analytics import (
    get_analysis_run_item,
    get_community,
    get_decades,
    get_summary,
    list_analysis_runs,
    list_communities,
)
from hmde.services.producers import run_meta

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/analysis-runs", response_model=AnalysisRunListResponse)
def list_analysis_runs_endpoint(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[Pagination, Depends(pagination)],
) -> AnalysisRunListResponse:
    items, total = list_analysis_runs(db, limit=page.limit, offset=page.offset)
    return AnalysisRunListResponse(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunListItem)
def get_analysis_run_endpoint(
    run_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisRunListItem:
    item = get_analysis_run_item(db, run_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return item


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def analytics_summary_endpoint(
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
) -> AnalyticsSummaryResponse:
    return get_summary(db, run)


@router.get("/analytics/decades", response_model=DecadeMetricResponse)
def analytics_decades_endpoint(
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
) -> DecadeMetricResponse:
    return DecadeMetricResponse(items=get_decades(db, run), meta=run_meta(run))


@router.get("/communities", response_model=CommunityListResponse)
def communities_endpoint(
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
    page: Annotated[Pagination, Depends(pagination)],
) -> CommunityListResponse:
    items, total = list_communities(db, run, limit=page.limit, offset=page.offset)
    return CommunityListResponse(
        items=items,
        total=total,
        limit=page.limit,
        offset=page.offset,
        meta=run_meta(run),
    )


@router.get("/communities/{community_key}", response_model=CommunityDetailResponse)
def community_endpoint(
    community_key: str,
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
) -> CommunityDetailResponse:
    community = get_community(db, run, community_key)
    if community is None:
        raise HTTPException(status_code=404, detail="Community not found")
    return community
