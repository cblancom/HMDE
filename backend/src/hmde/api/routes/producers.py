"""Producer API routes."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from hmde.api.dependencies import get_analysis_run
from hmde.api.pagination import Pagination, pagination
from hmde.db.session import get_db
from hmde.models import AnalysisRun
from hmde.schemas.api import (
    ProducerDetailResponse,
    ProducerGraphResponse,
    ProducerListResponse,
)
from hmde.services.producers import get_producer_detail, get_producer_graph, list_producers

router = APIRouter(prefix="/api/v1/producers", tags=["producers"])


@router.get("", response_model=ProducerListResponse)
def list_producers_endpoint(
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
    page: Annotated[Pagination, Depends(pagination)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    decade: Annotated[str | None, Query(pattern=r"^\d{4}s$")] = None,
    subgenre: Annotated[str | None, Query(max_length=50)] = None,
    sort: Literal["album_count", "band_count", "betweenness", "name"] = "album_count",
    order: Literal["asc", "desc"] = "desc",
) -> ProducerListResponse:
    items, total = list_producers(
        db,
        run,
        q=q,
        decade=decade,
        subgenre=subgenre,
        sort=sort,
        order=order,
        limit=page.limit,
        offset=page.offset,
    )
    return ProducerListResponse(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{producer_id}", response_model=ProducerDetailResponse)
def get_producer_endpoint(
    producer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
) -> ProducerDetailResponse:
    producer = get_producer_detail(db, run, producer_id)
    if producer is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Producer not found")
    return producer


@router.get("/{producer_id}/graph", response_model=ProducerGraphResponse)
def get_producer_graph_endpoint(
    producer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
    view: Literal["albums", "bands"] = "bands",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    depth: Annotated[int, Query(ge=1, le=2)] = 1,
    max_nodes: Annotated[int, Query(ge=1, le=500)] = 500,
    max_edges: Annotated[int, Query(ge=1, le=2000)] = 2000,
    include_evidence: bool = False,
) -> ProducerGraphResponse:
    graph = get_producer_graph(
        db,
        run,
        producer_id,
        view=view,
        limit=limit,
        depth=depth,
        max_nodes=max_nodes,
        max_edges=max_edges,
        include_evidence=include_evidence,
    )
    if graph is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Producer not found")
    return graph
