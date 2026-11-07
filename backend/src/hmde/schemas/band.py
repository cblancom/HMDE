"""Band API schemas."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class BandListItem(BaseModel):
    id: UUID
    mbid: str
    name: str
    country: str | None
    subgenre: str | None
    album_count: int


class BandListResponse(BaseModel):
    items: list[BandListItem]
    total: int
    limit: int
    offset: int


class CreditResponse(BaseModel):
    artist_id: UUID
    artist_name: str
    role: str
    role_name: str
    scope: str
    supporting_recording_count: int
    recording_count: int
    confidence: float
    status: str


class AlbumResponse(BaseModel):
    id: UUID
    mbid: str
    title: str
    year: int | None
    first_release_date: date | None
    credits: list[CreditResponse]


class BandDetailResponse(BaseModel):
    id: UUID
    mbid: str
    name: str
    country: str | None
    subgenre: str | None
    albums: list[AlbumResponse]
