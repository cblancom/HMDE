"""Read-only loading and support aggregation for E7 network analysis."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from hmde.models import QualityRun

ALBUMS_SQL = text(
    """
    SELECT rg.id AS album_id, rg.mbid AS album_mbid, rg.title AS album_title,
           rg.first_release_date,
           a.id AS band_id, a.name AS band_name, a.mbid AS band_mbid,
           a.type AS band_type, a.country AS band_country,
           rgs.subgenre_code AS primary_code, rgs.status AS primary_status
    FROM release_group rg
    JOIN artist a ON a.id = rg.artist_id
    LEFT JOIN release_group_subgenre rgs
      ON rgs.release_group_id = rg.id
     AND rgs.taxonomy_version = :taxonomy_version
     AND rgs.is_primary
    """
)
SECONDARY_SQL = text(
    """
    SELECT release_group_id, subgenre_code
    FROM release_group_subgenre
    WHERE taxonomy_version = :taxonomy_version AND NOT is_primary
    ORDER BY release_group_id, subgenre_code
    """
)
CREDITS_SQL = text(
    """
    SELECT c.id AS credit_id, c.artist_id AS producer_id, ca.name AS producer_name,
           ca.mbid AS producer_mbid, ca.type AS producer_type, ca.country AS producer_country,
           c.role_code, c.scope, c.release_group_id AS album_id, c.release_id, c.recording_id,
           c.credited_as, c.confidence, c.status, c.source_record_id
    FROM credit c
    JOIN artist ca ON ca.id = c.artist_id
    WHERE c.role_code IN ('producer', 'co-producer')
      AND c.release_group_id IS NOT NULL
    ORDER BY c.artist_id, c.release_group_id, c.role_code, c.id
    """
)
RECORDINGS_SQL = text(
    """
    SELECT r.release_group_id AS album_id, rr.release_id, rr.recording_id
    FROM release r
    JOIN recording_release rr ON rr.release_id = r.id
    ORDER BY r.release_group_id, rr.release_id, rr.recording_id
    """
)
QUALITY_SQL = text(
    """
    SELECT qf.severity, qf.status, count(*) AS count
    FROM quality_finding qf
    WHERE qf.quality_run_id = :quality_run_id
    GROUP BY qf.severity, qf.status
    ORDER BY qf.severity, qf.status
    """
)
EXCEPTIONS_SQL = text(
    """
    SELECT count(*) AS count
    FROM quality_exception
    WHERE catalogue_version = :catalogue_version AND status = 'active'
    """
)
DUPLICATE_LABELS_SQL = text(
    """
    SELECT lower(name) AS label, count(*) AS count
    FROM artist
    GROUP BY lower(name)
    HAVING count(*) > 1
    ORDER BY label
    """
)


@dataclass(frozen=True, slots=True)
class AlbumRow:
    album_id: uuid.UUID
    album_mbid: str
    album_title: str
    first_release_date: date | None
    band_id: uuid.UUID
    band_name: str
    band_mbid: str
    band_type: str
    band_country: str | None
    primary_code: str | None
    primary_status: str | None
    secondary_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProducerAlbumRoleRow:
    producer_id: uuid.UUID
    producer_name: str
    producer_mbid: str
    producer_type: str
    producer_country: str | None
    album_id: uuid.UUID
    role_code: str
    supporting_recordings: int
    album_recordings: int
    support_ratio: float | None
    has_release_group_scope: bool
    scope_mix: dict[str, int]
    evidence: dict[str, Any]


@dataclass(frozen=True, slots=True)
class QualitySummary:
    findings: dict[str, int]
    active_exceptions: int
    missing_dates: int
    unclassified_albums: int
    duplicate_labels: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class NetworkData:
    albums: dict[uuid.UUID, AlbumRow]
    producer_albums: tuple[ProducerAlbumRoleRow, ...]
    quality: QualitySummary


def load_network_data(session: Session, *, quality_run: QualityRun) -> NetworkData:
    taxonomy_version = quality_run.taxonomy_version
    albums = _load_albums(session, taxonomy_version=taxonomy_version)
    credit_rows = session.execute(CREDITS_SQL).mappings().all()
    recording_rows = session.execute(RECORDINGS_SQL).mappings().all()
    album_recordings, release_recordings = _recording_maps(recording_rows)
    producer_albums = aggregate_producer_albums(
        albums,
        credit_rows,
        album_recordings=album_recordings,
        release_recordings=release_recordings,
    )
    quality = _quality_summary(
        session,
        quality_run=quality_run,
        albums=albums,
    )
    return NetworkData(albums=albums, producer_albums=producer_albums, quality=quality)


def aggregate_producer_albums(
    albums: dict[uuid.UUID, AlbumRow],
    credit_rows: list[Any],
    *,
    album_recordings: dict[uuid.UUID, set[uuid.UUID]],
    release_recordings: dict[uuid.UUID, set[uuid.UUID]],
) -> tuple[ProducerAlbumRoleRow, ...]:
    grouped: dict[tuple[uuid.UUID, uuid.UUID, str], list[Any]] = defaultdict(list)
    for row in credit_rows:
        album_id = row["album_id"]
        if album_id not in albums:
            continue
        grouped[(row["producer_id"], album_id, row["role_code"])].append(row)

    results: list[ProducerAlbumRoleRow] = []
    for (producer_id, album_id, role_code), rows in sorted(
        grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]), item[0][2])
    ):
        first = rows[0]
        supporting: set[uuid.UUID] = set()
        release_group_scope = False
        scope_mix: dict[str, int] = defaultdict(int)
        credit_ids: list[str] = []
        source_ids: set[str] = set()
        credited_as: set[str] = set()
        statuses: set[str] = set()
        for row in rows:
            scope = str(row["scope"])
            scope_mix[scope] += 1
            credit_ids.append(str(row["credit_id"]))
            source_ids.add(str(row["source_record_id"]))
            if row["credited_as"]:
                credited_as.add(str(row["credited_as"]))
            statuses.add(str(row["status"]))
            if scope == "release_group":
                release_group_scope = True
            elif scope == "release" and row["release_id"] is not None:
                supporting.update(release_recordings.get(row["release_id"], set()))
            elif scope == "recording" and row["recording_id"] is not None:
                supporting.add(row["recording_id"])

        total_recordings = len(album_recordings.get(album_id, set()))
        ratio = _support_ratio(
            supporting=len(supporting),
            total=total_recordings,
            release_group_scope=release_group_scope,
        )
        results.append(
            ProducerAlbumRoleRow(
                producer_id=producer_id,
                producer_name=str(first["producer_name"]),
                producer_mbid=str(first["producer_mbid"]),
                producer_type=str(first["producer_type"]),
                producer_country=first["producer_country"],
                album_id=album_id,
                role_code=role_code,
                supporting_recordings=len(supporting),
                album_recordings=total_recordings,
                support_ratio=ratio,
                has_release_group_scope=release_group_scope,
                scope_mix=dict(sorted(scope_mix.items())),
                evidence={
                    "credit_ids": credit_ids,
                    "source_record_ids": sorted(source_ids),
                    "credited_as": sorted(credited_as),
                    "statuses": sorted(statuses),
                },
            )
        )
    return tuple(results)


def _support_ratio(*, supporting: int, total: int, release_group_scope: bool) -> float | None:
    if release_group_scope:
        return 1.0
    if total <= 0 or supporting <= 0:
        return None
    return min(1.0, supporting / total)


def _load_albums(session: Session, *, taxonomy_version: str) -> dict[uuid.UUID, AlbumRow]:
    rows = session.execute(ALBUMS_SQL, {"taxonomy_version": taxonomy_version}).mappings().all()
    secondary: dict[uuid.UUID, list[str]] = defaultdict(list)
    for row in session.execute(SECONDARY_SQL, {"taxonomy_version": taxonomy_version}).mappings():
        secondary[row["release_group_id"]].append(str(row["subgenre_code"]))
    albums: dict[uuid.UUID, AlbumRow] = {}
    for row in rows:
        album_id = row["album_id"]
        albums[album_id] = AlbumRow(
            album_id=album_id,
            album_mbid=str(row["album_mbid"]),
            album_title=str(row["album_title"]),
            first_release_date=row["first_release_date"],
            band_id=row["band_id"],
            band_name=str(row["band_name"]),
            band_mbid=str(row["band_mbid"]),
            band_type=str(row["band_type"]),
            band_country=row["band_country"],
            primary_code=row["primary_code"],
            primary_status=row["primary_status"],
            secondary_codes=tuple(secondary.get(album_id, [])),
        )
    return albums


def _recording_maps(
    rows: list[Any],
) -> tuple[dict[uuid.UUID, set[uuid.UUID]], dict[uuid.UUID, set[uuid.UUID]]]:
    album_recordings: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    release_recordings: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for row in rows:
        album_recordings[row["album_id"]].add(row["recording_id"])
        release_recordings[row["release_id"]].add(row["recording_id"])
    return dict(album_recordings), dict(release_recordings)


def _quality_summary(
    session: Session,
    *,
    quality_run: QualityRun,
    albums: dict[uuid.UUID, AlbumRow],
) -> QualitySummary:
    findings: dict[str, int] = {}
    for row in session.execute(QUALITY_SQL, {"quality_run_id": quality_run.id}).mappings():
        key = f"{row['severity']}:{row['status']}"
        findings[key] = int(row["count"])
    active_exceptions = int(
        session.execute(
            EXCEPTIONS_SQL, {"catalogue_version": quality_run.catalogue_version}
        ).scalar_one()
    )
    duplicate_labels = tuple(
        {"label": str(row["label"]), "count": int(row["count"])}
        for row in session.execute(DUPLICATE_LABELS_SQL).mappings()
    )
    return QualitySummary(
        findings=dict(sorted(findings.items())),
        active_exceptions=active_exceptions,
        missing_dates=sum(1 for album in albums.values() if album.first_release_date is None),
        unclassified_albums=sum(1 for album in albums.values() if album.primary_code is None),
        duplicate_labels=duplicate_labels,
    )


def filter_network_data(
    data: NetworkData,
    *,
    decade: str | None = None,
    subgenre: str | None = None,
    band_ids: tuple[uuid.UUID, ...] = (),
) -> NetworkData:
    if decade is None and subgenre is None and not band_ids:
        return data
    band_set = set(band_ids)
    albums: dict[uuid.UUID, AlbumRow] = {}
    for album in data.albums.values():
        if band_set and album.band_id not in band_set:
            continue
        if subgenre and album.primary_code != subgenre and subgenre not in album.secondary_codes:
            continue
        if decade is not None:
            if album.first_release_date is None:
                continue
            album_decade = f"{(album.first_release_date.year // 10) * 10}s"
            if album_decade != decade:
                continue
        albums[album.album_id] = album
    rows = tuple(row for row in data.producer_albums if row.album_id in albums)
    return NetworkData(albums=albums, producer_albums=rows, quality=data.quality)
