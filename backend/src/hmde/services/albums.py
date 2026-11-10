"""Album read services."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from hmde.models import (
    Artist,
    Credit,
    RecordingRelease,
    Release,
    ReleaseGroup,
    ReleaseGroupSubgenre,
    Role,
    Subgenre,
    TaxonomyVersion,
)
from hmde.schemas.api import (
    AlbumCreditResponse,
    AlbumDetailResponse,
    AlbumListItem,
)
from hmde.services.taxonomy import descendant_codes


def list_albums(
    session: Session,
    *,
    q: str | None,
    band_id: UUID | None,
    producer_id: UUID | None,
    decade: str | None,
    year_from: int | None,
    year_to: int | None,
    subgenre: str | None,
    include_unclassified: bool,
    limit: int,
    offset: int,
) -> tuple[list[AlbumListItem], int]:
    taxonomy_version = _taxonomy_version(session)
    conditions = []
    if q:
        conditions.append(ReleaseGroup.title.ilike(f"%{q.strip()}%"))
    if band_id:
        conditions.append(ReleaseGroup.artist_id == band_id)
    if producer_id:
        conditions.append(
            exists(
                select(Credit.id).where(
                    Credit.release_group_id == ReleaseGroup.id,
                    Credit.artist_id == producer_id,
                    Credit.role_code.in_(("producer", "co-producer")),
                )
            )
        )
    start = int(decade[:-1]) if decade else year_from
    end = start + 9 if decade else year_to
    if start is not None:
        conditions.append(func.extract("year", ReleaseGroup.first_release_date) >= start)
    if end is not None:
        conditions.append(func.extract("year", ReleaseGroup.first_release_date) <= end)
    if subgenre:
        codes = descendant_codes(session, subgenre) or {subgenre}
        conditions.append(
            exists(
                select(ReleaseGroupSubgenre.release_group_id).where(
                    ReleaseGroupSubgenre.release_group_id == ReleaseGroup.id,
                    ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
                    ReleaseGroupSubgenre.subgenre_code.in_(codes),
                )
            )
        )
    if not include_unclassified:
        conditions.append(
            exists(
                select(ReleaseGroupSubgenre.release_group_id).where(
                    ReleaseGroupSubgenre.release_group_id == ReleaseGroup.id,
                    ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
                    ReleaseGroupSubgenre.is_primary.is_(True),
                )
            )
        )

    producer_counts = (
        select(
            Credit.release_group_id.label("album_id"),
            func.count(func.distinct(Credit.artist_id)).label("producer_count"),
        )
        .where(Credit.role_code.in_(("producer", "co-producer")))
        .group_by(Credit.release_group_id)
        .subquery()
    )
    credit_counts = (
        select(
            Credit.release_group_id.label("album_id"),
            func.count(Credit.id).label("credit_count"),
        )
        .group_by(Credit.release_group_id)
        .subquery()
    )
    statement = (
        select(
            ReleaseGroup,
            Artist.name.label("band_name"),
            Subgenre.name.label("primary_subgenre"),
            func.coalesce(producer_counts.c.producer_count, 0).label("producer_count"),
            func.coalesce(credit_counts.c.credit_count, 0).label("credit_count"),
        )
        .join(Artist, Artist.id == ReleaseGroup.artist_id)
        .outerjoin(
            ReleaseGroupSubgenre,
            and_(
                ReleaseGroupSubgenre.release_group_id == ReleaseGroup.id,
                ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
                ReleaseGroupSubgenre.is_primary.is_(True),
            ),
        )
        .outerjoin(Subgenre, Subgenre.code == ReleaseGroupSubgenre.subgenre_code)
        .outerjoin(producer_counts, producer_counts.c.album_id == ReleaseGroup.id)
        .outerjoin(credit_counts, credit_counts.c.album_id == ReleaseGroup.id)
        .where(*conditions)
        .order_by(
            ReleaseGroup.first_release_date.is_(None),
            ReleaseGroup.first_release_date,
            ReleaseGroup.title,
            ReleaseGroup.id,
        )
        .limit(limit)
        .offset(offset)
    )
    total = session.scalar(select(func.count(ReleaseGroup.id)).where(*conditions)) or 0
    items = [
        AlbumListItem(
            id=group.id,
            mbid=group.mbid,
            title=group.title,
            band_id=group.artist_id,
            band_name=str(band_name),
            year=group.first_release_date.year if group.first_release_date else None,
            first_release_date=group.first_release_date,
            primary_subgenre=primary_subgenre,
            producer_count=int(producer_count),
            credit_count=int(credit_count),
        )
        for group, band_name, primary_subgenre, producer_count, credit_count in session.execute(
            statement
        ).all()
    ]
    return items, total


def get_album_detail(session: Session, album_id: UUID) -> AlbumDetailResponse | None:
    row = session.execute(
        select(ReleaseGroup, Artist.name.label("band_name"))
        .join(Artist, Artist.id == ReleaseGroup.artist_id)
        .where(ReleaseGroup.id == album_id)
    ).first()
    if row is None:
        return None
    album, band_name = row
    taxonomy_version = _taxonomy_version(session)
    primary = session.scalar(
        select(Subgenre.name)
        .join(ReleaseGroupSubgenre, ReleaseGroupSubgenre.subgenre_code == Subgenre.code)
        .where(
            ReleaseGroupSubgenre.release_group_id == album_id,
            ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
            ReleaseGroupSubgenre.is_primary.is_(True),
        )
    )
    secondary = list(
        session.scalars(
            select(Subgenre.name)
            .join(ReleaseGroupSubgenre, ReleaseGroupSubgenre.subgenre_code == Subgenre.code)
            .where(
                ReleaseGroupSubgenre.release_group_id == album_id,
                ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
                ReleaseGroupSubgenre.is_primary.is_(False),
            )
            .order_by(Subgenre.name)
        )
    )
    recording_count = int(
        session.scalar(
            select(func.count(func.distinct(RecordingRelease.recording_id)))
            .join(Release, Release.id == RecordingRelease.release_id)
            .where(Release.release_group_id == album_id)
        )
        or 0
    )
    credits = _album_credits(session, album_id=album_id, recording_count=recording_count)
    return AlbumDetailResponse(
        id=album.id,
        mbid=album.mbid,
        title=album.title,
        band_id=album.artist_id,
        band_name=str(band_name),
        year=album.first_release_date.year if album.first_release_date else None,
        first_release_date=album.first_release_date,
        primary_subgenre=primary,
        secondary_subgenres=secondary,
        credits=credits,
    )


def _album_credits(
    session: Session,
    *,
    album_id: UUID,
    recording_count: int,
) -> list[AlbumCreditResponse]:
    rows = session.execute(
        select(Credit, Artist.name, Role.name)
        .join(Artist, Artist.id == Credit.artist_id)
        .join(Role, Role.code == Credit.role_code)
        .where(Credit.release_group_id == album_id)
        .order_by(Role.name, Artist.name, Credit.id)
    ).all()
    grouped: dict[tuple[UUID, str], dict[str, object]] = defaultdict(dict)
    for credit, artist_name, role_name in rows:
        key = (credit.artist_id, credit.role_code)
        entry = grouped.setdefault(
            key,
            {
                "artist_name": artist_name,
                "role_name": role_name,
                "full": False,
                "recordings": set(),
                "confidence": 0.0,
                "statuses": set(),
            },
        )
        entry["full"] = bool(entry["full"]) or credit.scope in {"release_group", "release"}
        if credit.recording_id is not None:
            entry["recordings"].add(credit.recording_id)
        entry["confidence"] = max(float(entry["confidence"]), credit.confidence)
        entry["statuses"].add(credit.status)
    result: list[AlbumCreditResponse] = []
    for (artist_id, role_code), entry in sorted(
        grouped.items(), key=lambda item: (str(item[1]["role_name"]), str(item[1]["artist_name"]))
    ):
        supporting = recording_count if entry["full"] else len(entry["recordings"])
        ratio = min(1.0, supporting / recording_count) if recording_count else None
        statuses = entry["statuses"]
        result.append(
            AlbumCreditResponse(
                artist_id=artist_id,
                artist_name=str(entry["artist_name"]),
                role=role_code,
                role_name=str(entry["role_name"]),
                scope="release_group" if entry["full"] else "recording",
                supporting_recording_count=supporting,
                recording_count=recording_count,
                support_ratio=ratio,
                confidence=float(entry["confidence"]),
                status="confirmed" if "confirmed" in statuses else sorted(statuses)[0],
            )
        )
    return result


def _taxonomy_version(session: Session) -> str | None:
    return session.scalar(
        select(TaxonomyVersion.version).where(TaxonomyVersion.is_current.is_(True)).limit(1)
    )
