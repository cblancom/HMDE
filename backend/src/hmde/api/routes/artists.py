"""Artist API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from hmde.db.session import get_db
from hmde.schemas.api import ArtistDetailResponse
from hmde.services.catalog import get_artist_detail

router = APIRouter(prefix="/api/v1/artists", tags=["artists"])


@router.get("/{artist_id}", response_model=ArtistDetailResponse)
def get_artist_endpoint(
    artist_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ArtistDetailResponse:
    artist = get_artist_detail(db, artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist
