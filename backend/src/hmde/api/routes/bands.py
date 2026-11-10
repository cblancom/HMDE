"""Band API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from hmde.db.session import get_db
from hmde.schemas.band import BandDetailResponse, BandListResponse
from hmde.schemas.graph import BandGraphResponse
from hmde.services.catalog import get_band_detail, list_bands
from hmde.services.graph import get_band_graph

router = APIRouter(prefix="/api/v1/bands", tags=["bands"])


@router.get("", response_model=BandListResponse)
def list_bands_endpoint(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    subgenre: Annotated[str | None, Query(max_length=50)] = None,
    decade: Annotated[str | None, Query(pattern=r"^\d{4}s$")] = None,
    year_from: Annotated[int | None, Query(ge=1960, le=2026)] = None,
    year_to: Annotated[int | None, Query(ge=1960, le=2026)] = None,
    include_retired: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BandListResponse:
    items, total = list_bands(
        db,
        q,
        subgenre,
        limit,
        offset,
        decade=decade,
        year_from=year_from,
        year_to=year_to,
        include_retired=include_retired,
    )
    return BandListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{band_id}", response_model=BandDetailResponse)
def get_band_endpoint(
    band_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> BandDetailResponse:
    detail = get_band_detail(db, band_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Band not found")
    return detail


@router.get("/{band_id}/graph", response_model=BandGraphResponse)
def get_band_graph_endpoint(
    band_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> BandGraphResponse:
    graph = get_band_graph(db, band_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Band not found")
    return graph
