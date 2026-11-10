"""Credit API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from hmde.api.pagination import Pagination, pagination
from hmde.db.session import get_db
from hmde.schemas.api import CreditListResponse
from hmde.services.credits import list_credits

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])


@router.get("", response_model=CreditListResponse)
def list_credits_endpoint(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[Pagination, Depends(pagination)],
    album_id: UUID | None = None,
    band_id: UUID | None = None,
    artist_id: UUID | None = None,
    role: Annotated[str | None, Query(max_length=50)] = None,
    scope: Annotated[str | None, Query(pattern=r"^(release_group|release|recording)$")] = None,
) -> CreditListResponse:
    items, total = list_credits(
        db,
        album_id=album_id,
        band_id=band_id,
        artist_id=artist_id,
        role=role,
        scope=scope,
        limit=page.limit,
        offset=page.offset,
    )
    return CreditListResponse(items=items, total=total, limit=page.limit, offset=page.offset)
