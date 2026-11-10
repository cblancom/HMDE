"""Catalog read services."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import exists, extract, func, select
from sqlalchemy.orm import Session

from hmde.models import (
    Artist,
    ArtistSubgenre,
    Credit,
    DatasetMembership,
    NormalizationRun,
    RecordingRelease,
    Release,
    ReleaseGroup,
    Role,
    Subgenre,
)
from hmde.schemas.api import ArtistDetailResponse
from hmde.schemas.band import (
    AlbumResponse,
    BandDetailResponse,
    BandListItem,
    CreditResponse,
)
from hmde.services.taxonomy import descendant_codes


def list_bands(
    session: Session,
    q: str | None,
    subgenre: str | None,
    limit: int,
    offset: int,
    *,
    decade: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    include_retired: bool = False,
) -> tuple[list[BandListItem], int]:
    conditions = [ArtistSubgenre.is_primary.is_(True)]
    query_text = (q or "").strip()
    if query_text:
        conditions.append(Artist.name.ilike(f"%{query_text}%"))
    if subgenre:
        codes = descendant_codes(session, subgenre) or {subgenre}
        conditions.append(ArtistSubgenre.subgenre_code.in_(codes))
    if decade or year_from is not None or year_to is not None:
        start = int(decade[:-1]) if decade else year_from
        end = start + 9 if decade else year_to
        album_conditions = [ReleaseGroup.artist_id == Artist.id]
        if start is not None:
            album_conditions.append(extract("year", ReleaseGroup.first_release_date) >= start)
        if end is not None:
            album_conditions.append(extract("year", ReleaseGroup.first_release_date) <= end)
        conditions.append(exists(select(ReleaseGroup.id).where(*album_conditions)))
    if not include_retired:
        dataset_version = _latest_dataset_version(session)
        if dataset_version is not None:
            conditions.append(
                ~exists(
                    select(DatasetMembership.artist_id).where(
                        DatasetMembership.artist_id == Artist.id,
                        DatasetMembership.dataset_version == dataset_version,
                        DatasetMembership.lifecycle == "retired",
                    )
                )
            )

    album_counts = (
        select(
            ReleaseGroup.artist_id.label("artist_id"),
            func.count(ReleaseGroup.id).label("album_count"),
        )
        .group_by(ReleaseGroup.artist_id)
        .subquery()
    )

    statement = (
        select(
            Artist.id,
            Artist.mbid,
            Artist.name,
            Artist.country,
            Subgenre.name.label("subgenre"),
            func.coalesce(album_counts.c.album_count, 0).label("album_count"),
        )
        .select_from(Artist)
        .join(ArtistSubgenre, ArtistSubgenre.artist_id == Artist.id)
        .join(Subgenre, Subgenre.code == ArtistSubgenre.subgenre_code)
        .outerjoin(album_counts, album_counts.c.artist_id == Artist.id)
        .where(*conditions)
        .order_by(Artist.name, Artist.id)
        .limit(limit)
        .offset(offset)
    )

    total_statement = (
        select(func.count(func.distinct(Artist.id)))
        .select_from(Artist)
        .join(ArtistSubgenre, ArtistSubgenre.artist_id == Artist.id)
        .where(*conditions)
    )

    rows = session.execute(statement).all()
    total = session.scalar(total_statement) or 0

    items = [
        BandListItem(
            id=row.id,
            mbid=row.mbid,
            name=row.name,
            country=row.country,
            subgenre=row.subgenre,
            album_count=row.album_count,
        )
        for row in rows
    ]
    return items, total


def get_artist_detail(session: Session, artist_id: UUID) -> ArtistDetailResponse | None:
    artist = session.get(Artist, artist_id)
    if artist is None:
        return None
    return ArtistDetailResponse(
        id=artist.id,
        mbid=artist.mbid,
        name=artist.name,
        type=artist.type,
        country=artist.country,
        disambiguation=artist.disambiguation,
    )


def get_band_detail(session: Session, band_id: UUID) -> BandDetailResponse | None:
    band_row = session.execute(
        select(Artist, Subgenre.name)
        .join(ArtistSubgenre, ArtistSubgenre.artist_id == Artist.id)
        .join(Subgenre, Subgenre.code == ArtistSubgenre.subgenre_code)
        .where(
            Artist.id == band_id,
            ArtistSubgenre.is_primary.is_(True),
        )
    ).first()
    if band_row is None:
        return None

    artist, subgenre_name = band_row
    groups = session.scalars(
        select(ReleaseGroup)
        .where(ReleaseGroup.artist_id == band_id)
        .order_by(
            ReleaseGroup.first_release_date.is_(None),
            ReleaseGroup.first_release_date,
            ReleaseGroup.title,
        )
    ).all()
    album_ids = [group.id for group in groups]

    recording_counts: dict[UUID, int] = {}
    credit_rows = []
    if album_ids:
        recording_counts = dict(
            session.execute(
                select(
                    Release.release_group_id,
                    func.count(func.distinct(RecordingRelease.recording_id)),
                )
                .join(RecordingRelease, RecordingRelease.release_id == Release.id)
                .where(Release.release_group_id.in_(album_ids))
                .group_by(Release.release_group_id)
            ).all()
        )
        credit_rows = session.execute(
            select(Credit, Artist.name, Role.name)
            .join(Artist, Credit.artist_id == Artist.id)
            .join(Role, Credit.role_code == Role.code)
            .where(Credit.release_group_id.in_(album_ids))
            .order_by(Artist.name, Role.name)
        ).all()

    aggregated: dict[tuple[UUID, UUID, str], dict[str, object]] = {}
    for credit, artist_name, role_name in credit_rows:
        key = (credit.release_group_id, credit.artist_id, credit.role_code)
        entry = aggregated.setdefault(
            key,
            {
                "artist_name": artist_name,
                "role_name": role_name,
                "has_full_album": False,
                "recording_ids": set(),
                "confidence": credit.confidence,
                "statuses": set(),
            },
        )
        if credit.scope in {"release", "release_group"}:
            entry["has_full_album"] = True
        if credit.recording_id is not None:
            entry["recording_ids"].add(credit.recording_id)
        entry["confidence"] = max(float(entry["confidence"]), credit.confidence)
        entry["statuses"].add(credit.status)

    credits_by_album: dict[UUID, list[CreditResponse]] = defaultdict(list)
    for (release_group_id, artist_id, role_code), entry in aggregated.items():
        total_recordings = recording_counts.get(release_group_id, 0)
        recording_ids = entry["recording_ids"]
        has_full_album = bool(entry["has_full_album"])
        recording_count = max(total_recordings, len(recording_ids))
        supporting_count = recording_count if has_full_album else len(recording_ids)
        statuses = entry["statuses"]
        status = "confirmed" if "confirmed" in statuses else sorted(statuses)[0]
        credits_by_album[release_group_id].append(
            CreditResponse(
                artist_id=artist_id,
                artist_name=str(entry["artist_name"]),
                role=role_code,
                role_name=str(entry["role_name"]),
                scope="release" if has_full_album else "recording",
                supporting_recording_count=supporting_count,
                recording_count=recording_count,
                confidence=float(entry["confidence"]),
                status=status,
            )
        )

    albums = [
        AlbumResponse(
            id=group.id,
            mbid=group.mbid,
            title=group.title,
            year=group.first_release_date.year if group.first_release_date else None,
            first_release_date=group.first_release_date,
            credits=sorted(
                credits_by_album.get(group.id, []),
                key=lambda credit: (credit.role_name, credit.artist_name),
            ),
        )
        for group in groups
    ]

    return BandDetailResponse(
        id=artist.id,
        mbid=artist.mbid,
        name=artist.name,
        country=artist.country,
        subgenre=subgenre_name,
        albums=albums,
    )


def _latest_dataset_version(session: Session) -> str | None:
    return session.scalar(
        select(NormalizationRun.dataset_version)
        .where(NormalizationRun.status.in_(("completed", "completed_with_review")))
        .order_by(NormalizationRun.finished_at.desc(), NormalizationRun.started_at.desc())
        .limit(1)
    )
