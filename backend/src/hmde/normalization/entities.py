"""Canonical entity and provenance normalization."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import (
    Artist,
    ExternalId,
    Recording,
    RecordingRelease,
    Release,
    ReleaseGroup,
)

from .errors import InputValidationError, ProvenanceError
from .ids import stable_uuid
from .inputs import NormalizationInputs
from .provenance import ensure_source_records


@dataclass(frozen=True, slots=True)
class EntityCounts:
    artists_created: int
    artists_updated: int
    release_groups_created: int
    release_groups_updated: int
    releases_created: int
    releases_updated: int
    recordings_created: int
    recordings_updated: int
    recording_releases_created: int
    recording_releases_updated: int
    external_ids_created: int
    source_records: int


@dataclass(frozen=True, slots=True)
class EntityIndex:
    source_records: dict[uuid.UUID, uuid.UUID]
    artists: dict[str, uuid.UUID]
    release_groups: dict[str, uuid.UUID]
    releases: dict[str, uuid.UUID]
    recordings: dict[str, uuid.UUID]
    recording_release_groups: dict[str, frozenset[uuid.UUID]]
    counts: EntityCounts


def normalize_entities(session: Session, inputs: NormalizationInputs) -> EntityIndex:
    dataset = inputs.dataset
    artists_rows = read_ndjson(dataset.file("artists.ndjson").path)
    group_rows = read_ndjson(dataset.file("release_groups.ndjson").path)
    release_rows = read_ndjson(dataset.file("releases.ndjson").path)
    recording_rows = read_ndjson(dataset.file("recordings.ndjson").path)
    link_rows = read_ndjson(dataset.file("release_recordings.ndjson").path)
    external_rows = read_ndjson(dataset.file("external_ids.ndjson").path)
    credit_rows = read_ndjson(dataset.file("credits.ndjson").path)

    raw_ids = _raw_ids(
        artists_rows,
        group_rows,
        release_rows,
        recording_rows,
        link_rows,
        external_rows,
        credit_rows,
    )
    source_records = ensure_source_records(
        session,
        raw_ids,
        dataset_version=dataset.dataset_version,
    )

    artist_ids, artist_counts = _normalize_artists(session, artists_rows, source_records)
    group_ids, group_counts = _normalize_release_groups(
        session,
        group_rows,
        artist_ids,
        source_records,
    )
    release_ids, release_counts = _normalize_releases(
        session,
        release_rows,
        group_ids,
        source_records,
    )
    recording_ids, recording_counts = _normalize_recordings(
        session,
        recording_rows,
        source_records,
    )
    link_counts = _normalize_recording_releases(
        session,
        link_rows,
        release_ids,
        recording_ids,
    )
    external_count = _normalize_external_ids(
        session,
        external_rows,
        artist_ids,
        source_records,
    )
    release_to_group = {
        _mbid(row, "release"): group_ids[_mbid(row, "release group", key="release_group_mbid")]
        for row in release_rows
    }
    recording_groups = _recording_groups(link_rows, release_ids, release_to_group)
    session.flush()

    counts = EntityCounts(
        artists_created=artist_counts[0],
        artists_updated=artist_counts[1],
        release_groups_created=group_counts[0],
        release_groups_updated=group_counts[1],
        releases_created=release_counts[0],
        releases_updated=release_counts[1],
        recordings_created=recording_counts[0],
        recordings_updated=recording_counts[1],
        recording_releases_created=link_counts[0],
        recording_releases_updated=link_counts[1],
        external_ids_created=external_count,
        source_records=len(source_records),
    )
    return EntityIndex(
        source_records=source_records,
        artists=artist_ids,
        release_groups=group_ids,
        releases=release_ids,
        recordings=recording_ids,
        recording_release_groups=recording_groups,
        counts=counts,
    )


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"could not read NDJSON file: {path}") from exc


def _normalize_artists(
    session: Session,
    rows: list[dict[str, Any]],
    source_records: dict[uuid.UUID, uuid.UUID],
) -> tuple[dict[str, uuid.UUID], tuple[int, int]]:
    mbids = {_mbid(row, "artist") for row in rows}
    existing = {
        row.mbid: row for row in session.scalars(select(Artist).where(Artist.mbid.in_(mbids)))
    }
    ids: dict[str, uuid.UUID] = {}
    created = updated = 0
    for row in rows:
        mbid = _mbid(row, "artist")
        source_id = _source_id(row, source_records)
        artist = existing.get(mbid)
        values = {
            "name": _required(row, "name"),
            "sort_name": _optional(row, "sort_name"),
            "type": _artist_type(row.get("type")),
            "country": _optional(row, "country"),
            "disambiguation": _optional(row, "disambiguation"),
            "source_record_id": source_id,
        }
        if artist is None:
            artist = Artist(
                id=stable_uuid("artist", mbid),
                mbid=mbid,
                **values,
            )
            session.add(artist)
            created += 1
        else:
            for key, value in values.items():
                setattr(artist, key, value)
            updated += 1
        ids[mbid] = artist.id
    session.flush()
    return ids, (created, updated)


def _normalize_release_groups(
    session: Session,
    rows: list[dict[str, Any]],
    artist_ids: dict[str, uuid.UUID],
    source_records: dict[uuid.UUID, uuid.UUID],
) -> tuple[dict[str, uuid.UUID], tuple[int, int]]:
    mbids = {_mbid(row, "release group") for row in rows}
    existing = {
        row.mbid: row
        for row in session.scalars(select(ReleaseGroup).where(ReleaseGroup.mbid.in_(mbids)))
    }
    ids: dict[str, uuid.UUID] = {}
    created = updated = 0
    for row in rows:
        mbid = _mbid(row, "release group")
        artist_mbid = _mbid(row, "artist", key="artist_mbid")
        try:
            artist_id = artist_ids[artist_mbid]
        except KeyError as exc:
            raise ProvenanceError(
                f"release group {mbid} references unknown artist {artist_mbid}"
            ) from exc
        release_date = _parse_date(row.get("first_release_date"))
        precision = _optional(row, "date_precision") or _precision(row.get("first_release_date"))
        values = {
            "artist_id": artist_id,
            "title": _required(row, "title"),
            "first_release_date": release_date,
            "first_release_precision": precision,
            "primary_type": _required(row, "primary_type"),
            "secondary_types": list(row.get("secondary_types") or []),
            "disambiguation": _optional(row, "disambiguation"),
            "source_record_id": _source_id(row, source_records),
        }
        group = existing.get(mbid)
        if group is None:
            group = ReleaseGroup(id=stable_uuid("release-group", mbid), mbid=mbid, **values)
            session.add(group)
            created += 1
        else:
            for key, value in values.items():
                setattr(group, key, value)
            updated += 1
        ids[mbid] = group.id
    session.flush()
    return ids, (created, updated)


def _normalize_releases(
    session: Session,
    rows: list[dict[str, Any]],
    group_ids: dict[str, uuid.UUID],
    source_records: dict[uuid.UUID, uuid.UUID],
) -> tuple[dict[str, uuid.UUID], tuple[int, int]]:
    mbids = {_mbid(row, "release") for row in rows}
    existing = {
        row.mbid: row for row in session.scalars(select(Release).where(Release.mbid.in_(mbids)))
    }
    ids: dict[str, uuid.UUID] = {}
    created = updated = 0
    for row in rows:
        mbid = _mbid(row, "release")
        group_mbid = _mbid(row, "release group", key="release_group_mbid")
        try:
            group_id = group_ids[group_mbid]
        except KeyError as exc:
            raise ProvenanceError(f"release {mbid} references unknown group {group_mbid}") from exc
        values = {
            "release_group_id": group_id,
            "title": _required(row, "title"),
            "release_date": _parse_date(row.get("date")),
            "release_date_precision": _precision(row.get("date")),
            "country": _optional(row, "country"),
            "status": _optional(row, "status"),
            "source_record_id": _source_id(row, source_records),
        }
        release = existing.get(mbid)
        if release is None:
            release = Release(id=stable_uuid("release", mbid), mbid=mbid, **values)
            session.add(release)
            created += 1
        else:
            for key, value in values.items():
                setattr(release, key, value)
            updated += 1
        ids[mbid] = release.id
    session.flush()
    return ids, (created, updated)


def _normalize_recordings(
    session: Session,
    rows: list[dict[str, Any]],
    source_records: dict[uuid.UUID, uuid.UUID],
) -> tuple[dict[str, uuid.UUID], tuple[int, int]]:
    mbids = {_mbid(row, "recording") for row in rows}
    existing = {
        row.mbid: row for row in session.scalars(select(Recording).where(Recording.mbid.in_(mbids)))
    }
    ids: dict[str, uuid.UUID] = {}
    created = updated = 0
    for row in rows:
        mbid = _mbid(row, "recording")
        values = {
            "title": _required(row, "title"),
            "source_record_id": _source_id(row, source_records),
        }
        recording = existing.get(mbid)
        if recording is None:
            recording = Recording(id=stable_uuid("recording", mbid), mbid=mbid, **values)
            session.add(recording)
            created += 1
        else:
            for key, value in values.items():
                setattr(recording, key, value)
            updated += 1
        ids[mbid] = recording.id
    session.flush()
    return ids, (created, updated)


def _normalize_recording_releases(
    session: Session,
    rows: list[dict[str, Any]],
    release_ids: dict[str, uuid.UUID],
    recording_ids: dict[str, uuid.UUID],
) -> tuple[int, int]:
    release_values = set(release_ids.values())
    existing = {
        (row.release_id, row.recording_id): row
        for row in session.scalars(
            select(RecordingRelease).where(RecordingRelease.release_id.in_(release_values))
        )
    }
    created = updated = 0
    for row in rows:
        release_mbid = _mbid(row, "release", key="release_mbid")
        recording_mbid = _mbid(row, "recording", key="recording_mbid")
        try:
            release_id = release_ids[release_mbid]
            recording_id = recording_ids[recording_mbid]
        except KeyError as exc:
            raise ProvenanceError(f"recording link references unknown entity: {row}") from exc
        key = (release_id, recording_id)
        values = {
            "disc": _optional(row, "disc"),
            "position": _optional(row, "position"),
            "track_number": _optional(row, "track_number"),
        }
        link = existing.get(key)
        if link is None:
            link = RecordingRelease(
                id=stable_uuid("recording-release", f"{release_id}:{recording_id}"),
                release_id=release_id,
                recording_id=recording_id,
                **values,
            )
            session.add(link)
            existing[key] = link
            created += 1
        else:
            for name, value in values.items():
                setattr(link, name, value)
            updated += 1
    session.flush()
    return created, updated


def _normalize_external_ids(
    session: Session,
    rows: list[dict[str, Any]],
    artist_ids: dict[str, uuid.UUID],
    source_records: dict[uuid.UUID, uuid.UUID],
) -> int:
    existing = {
        (row.entity_type, row.entity_id, row.source, row.external_id)
        for row in session.scalars(
            select(ExternalId).where(
                ExternalId.entity_id.in_(set(artist_ids.values())),
            )
        )
    }
    created = 0
    for row in rows:
        entity_type = _required(row, "entity_type")
        if entity_type != "artist":
            continue
        entity_mbid = _mbid(row, "artist", key="entity_mbid")
        try:
            entity_id = artist_ids[entity_mbid]
        except KeyError as exc:
            raise ProvenanceError(f"external id references unknown artist: {entity_mbid}") from exc
        source = _required(row, "source")
        external_id = _required(row, "external_id")
        key = (entity_type, entity_id, source, external_id)
        if key in existing:
            continue
        session.add(
            ExternalId(
                id=stable_uuid(
                    "external-id",
                    f"{entity_type}:{entity_id}:{source}:{external_id}",
                ),
                entity_type=entity_type,
                entity_id=entity_id,
                source=source,
                external_id=external_id,
                url=_optional(row, "url"),
            )
        )
        existing.add(key)
        created += 1
    session.flush()
    return created


def _recording_groups(
    rows: list[dict[str, Any]],
    release_ids: dict[str, uuid.UUID],
    release_to_group: dict[str, uuid.UUID],
) -> dict[str, frozenset[uuid.UUID]]:
    groups: dict[str, set[uuid.UUID]] = {}
    for row in rows:
        release_mbid = _mbid(row, "release", key="release_mbid")
        recording_mbid = _mbid(row, "recording", key="recording_mbid")
        if release_mbid not in release_ids:
            continue
        group_id = release_to_group.get(release_mbid)
        if group_id is not None:
            groups.setdefault(recording_mbid, set()).add(group_id)
    return {key: frozenset(value) for key, value in groups.items()}


def _raw_ids(*record_sets: Iterable[dict[str, Any]]) -> set[uuid.UUID]:
    ids: set[uuid.UUID] = set()
    for records in record_sets:
        for row in records:
            raw_id = row.get("raw_response_id")
            if not isinstance(raw_id, str):
                raise InputValidationError("NDJSON record is missing raw_response_id")
            try:
                ids.add(uuid.UUID(raw_id))
            except ValueError as exc:
                raise InputValidationError("NDJSON record has an invalid raw_response_id") from exc
    return ids


def _source_id(row: dict[str, Any], source_records: dict[uuid.UUID, uuid.UUID]) -> uuid.UUID:
    raw_id = _uuid_value(row, "raw_response_id", "raw response")
    try:
        return source_records[raw_id]
    except KeyError as exc:
        raise ProvenanceError(f"missing source record for raw response {raw_id}") from exc


def _mbid(row: dict[str, Any], label: str, *, key: str = "mbid") -> str:
    return str(_uuid_value(row, key, label))


def _uuid_value(row: dict[str, Any], key: str, label: str) -> uuid.UUID:
    value = _required(row, key)
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise InputValidationError(f"invalid {label} MBID: {value!r}") from exc


def _required(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"record is missing a valid {key}")
    return value.strip()


def _optional(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _artist_type(value: object) -> str:
    if not isinstance(value, str):
        return "other"
    normalized = value.casefold()
    return normalized if normalized in {"person", "group", "other"} else "other"


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        if len(text) == 4 and text.isdigit():
            return date(int(text), 1, 1)
        if len(text) == 7 and text[4:5] == "-":
            return date(int(text[:4]), int(text[5:7]), 1)
        return date.fromisoformat(text)
    except ValueError as exc:
        raise InputValidationError(f"invalid date: {value!r}") from exc


def _precision(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "unknown"
    parts = value.split("-")
    if len(parts) == 3:
        return "day"
    if len(parts) == 2:
        return "month"
    return "year"
