"""Album API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from hmde.api.pagination import Pagination, pagination
from hmde.db.session import get_db
from hmde.schemas.api import AlbumDetailResponse, AlbumListResponse
from hmde.services.albums import get_album_detail, list_albums

router = APIRouter(prefix="/api/v1/albums", tags=["albums"])


@router.get("", response_model=AlbumListResponse)
def list_albums_endpoint(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[Pagination, Depends(pagination)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    band_id: UUID | None = None,
    producer_id: UUID | None = None,
    decade: Annotated[str | None, Query(pattern=r"^\d{4}s$")] = None,
    year_from: Annotated[int | None, Query(ge=1960, le=2026)] = None,
    year_to: Annotated[int | None, Query(ge=1960, le=2026)] = None,
    subgenre: Annotated[str | None, Query(max_length=50)] = None,
    include_unclassified: bool = True,
) -> AlbumListResponse:
    items, total = list_albums(
        db,
        q=q,
        band_id=band_id,
        producer_id=producer_id,
        decade=decade,
        year_from=year_from,
        year_to=year_to,
        subgenre=subgenre,
        include_unclassified=include_unclassified,
        limit=page.limit,
        offset=page.offset,
    )
    return AlbumListResponse(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{album_id}", response_model=AlbumDetailResponse)
def get_album_endpoint(
    album_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> AlbumDetailResponse:
    album = get_album_detail(db, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    return album
