"""Graph API routes."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from hmde.api.dependencies import get_analysis_run
from hmde.db.session import get_db
from hmde.models import AnalysisRun
from hmde.schemas.api import ProducerOverviewGraphResponse
from hmde.services.producers import get_producer_overview_graph

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("/producers", response_model=ProducerOverviewGraphResponse)
def get_producer_overview_graph_endpoint(
    db: Annotated[Session, Depends(get_db)],
    run: Annotated[AnalysisRun, Depends(get_analysis_run)],
    view: Literal["albums", "bands"] = "bands",
    producer_limit: Annotated[int, Query(ge=0, le=1000)] = 0,
    producer_sort: Literal["album_count", "band_count", "betweenness", "name"] = "album_count",
    order: Literal["asc", "desc"] = "desc",
    decade: Annotated[str | None, Query(pattern=r"^\d{4}s$")] = None,
    subgenre: Annotated[str | None, Query(max_length=50)] = None,
    include_isolated: bool = True,
    include_evidence: bool = False,
    max_nodes: Annotated[int, Query(ge=1, le=1000)] = 1000,
    max_edges: Annotated[int, Query(ge=1, le=2000)] = 2000,
) -> ProducerOverviewGraphResponse:
    return get_producer_overview_graph(
        db,
        run,
        view=view,
        producer_limit=producer_limit,
        producer_sort=producer_sort,
        order=order,
        decade=decade,
        subgenre=subgenre,
        include_isolated=include_isolated,
        include_evidence=include_evidence,
        max_nodes=max_nodes,
        max_edges=max_edges,
    )
