"""Versioned extracted dataset writer."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from hmde.etl.musicbrainz.traversal import BandExtraction, ExclusionRecord

SCHEMA_VERSION = "1"
MUSICBRAINZ_API_VERSION = "2"
DATASET_FORMAT = "ndjson"
MULTI_ARTIST_RELEASE_GROUP_REASON = "multi_artist_release_group"

ARTISTS_FILE = "artists.ndjson"
EXTERNAL_IDS_FILE = "external_ids.ndjson"
RELEASE_GROUPS_FILE = "release_groups.ndjson"
RELEASES_FILE = "releases.ndjson"
RECORDINGS_FILE = "recordings.ndjson"
RELEASE_RECORDINGS_FILE = "release_recordings.ndjson"
CREDITS_FILE = "credits.ndjson"
PLACES_FILE = "places.ndjson"
EXCLUSIONS_FILE = "exclusions.ndjson"
MANIFEST_FILE = "manifest.json"


class DatasetError(Exception):
    """Base error for dataset writing."""


class DatasetConflictError(DatasetError):
    """An existing dataset directory does not match the new manifest."""


@dataclass(frozen=True, slots=True)
class DatasetWriteResult:
    dataset_version: str
    path: Path
    manifest: dict[str, Any]


def write_dataset(
    extractions: Iterable[BandExtraction],
    output_root: Path,
    *,
    seed_list_version: str,
    taxonomy_version: str | None = None,
    period_start: date | str | None = None,
    period_end: date | str | None = None,
    batch_ids: Sequence[str] = (),
    source_snapshot_at: datetime,
    code_version: str,
) -> DatasetWriteResult:
    extraction_list = list(extractions)
    files = _build_files(extraction_list)
    source_snapshot = source_snapshot_at.astimezone(UTC)
    dataset_version = _dataset_version(
        files,
        seed_list_version=seed_list_version,
        taxonomy_version=taxonomy_version,
        period_start=period_start,
        period_end=period_end,
        batch_ids=batch_ids,
        source_snapshot_at=source_snapshot,
        code_version=code_version,
    )
    manifest = _build_manifest(
        files,
        extraction_list,
        dataset_version=dataset_version,
        seed_list_version=seed_list_version,
        taxonomy_version=taxonomy_version,
        period_start=period_start,
        period_end=period_end,
        batch_ids=batch_ids,
        source_snapshot_at=source_snapshot,
        code_version=code_version,
    )
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / dataset_version

    if target.exists():
        existing = json.loads((target / MANIFEST_FILE).read_text(encoding="utf-8"))
        if existing == manifest:
            return DatasetWriteResult(dataset_version, target, manifest)
        raise DatasetConflictError(f"dataset already exists with different content: {target}")

    temporary = Path(tempfile.mkdtemp(prefix=f".{dataset_version}.", dir=output_root))
    try:
        for name, data in files.items():
            (temporary / name).write_bytes(data)
        (temporary / MANIFEST_FILE).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, target)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return DatasetWriteResult(dataset_version, target, manifest)


def _build_files(extractions: list[BandExtraction]) -> dict[str, bytes]:
    artists = _canonical_records(
        [extraction.artist for extraction in extractions],
        key=lambda item: (item.mbid,),
    )
    external_ids = _canonical_records(
        [item for extraction in extractions for item in extraction.external_ids],
        key=lambda item: (
            item.entity_type,
            item.entity_mbid,
            item.source,
            item.external_id,
        ),
    )

    raw_release_groups = [item for extraction in extractions for item in extraction.release_groups]
    group_artists: dict[str, set[str]] = {}
    for group in raw_release_groups:
        group_artists.setdefault(group.mbid, set()).add(group.artist_mbid)
    excluded_group_mbids = {
        mbid for mbid, artist_mbids in group_artists.items() if len(artist_mbids) > 1
    }
    release_groups = _canonical_records(
        [group for group in raw_release_groups if group.mbid not in excluded_group_mbids],
        key=lambda item: (item.mbid,),
    )
    valid_group_mbids = {group.mbid for group in release_groups}

    releases = _canonical_records(
        [
            release
            for extraction in extractions
            for release in extraction.releases
            if release.release_group_mbid in valid_group_mbids
        ],
        key=lambda item: (item.mbid,),
    )
    valid_release_mbids = {release.mbid for release in releases}

    release_recordings = _canonical_records(
        [
            link
            for extraction in extractions
            for link in extraction.release_recordings
            if link.release_mbid in valid_release_mbids
        ],
        key=lambda item: (
            item.release_mbid,
            item.disc or "",
            item.position or "",
            item.track_number or "",
            item.recording_mbid,
        ),
    )
    referenced_recording_mbids = {link.recording_mbid for link in release_recordings}
    recordings = _canonical_records(
        [
            recording
            for extraction in extractions
            for recording in extraction.recordings
            if recording.mbid in referenced_recording_mbids
        ],
        key=lambda item: (item.mbid,),
    )
    valid_recording_mbids = {recording.mbid for recording in recordings}
    release_recordings = [
        link for link in release_recordings if link.recording_mbid in valid_recording_mbids
    ]

    credits = [
        credit
        for extraction in extractions
        for credit in extraction.credits
        if _target_is_canonical(
            credit,
            group_mbids=valid_group_mbids,
            release_mbids=valid_release_mbids,
            recording_mbids=valid_recording_mbids,
        )
    ]
    places = [
        place
        for extraction in extractions
        for place in extraction.places
        if _target_is_canonical(
            place,
            group_mbids=valid_group_mbids,
            release_mbids=valid_release_mbids,
            recording_mbids=valid_recording_mbids,
        )
    ]
    raw_exclusions = [item for extraction in extractions for item in extraction.exclusions]
    exclusions = _canonical_records(
        [
            *raw_exclusions,
            *_multi_artist_exclusions(raw_release_groups, excluded_group_mbids),
        ],
        key=lambda item: (item.release_group_mbid, item.reason),
    )

    return {
        ARTISTS_FILE: _ndjson(artists, key=lambda item: (item.mbid,)),
        EXTERNAL_IDS_FILE: _ndjson(
            external_ids,
            key=lambda item: (
                item.entity_type,
                item.entity_mbid,
                item.source,
                item.external_id,
            ),
        ),
        RELEASE_GROUPS_FILE: _ndjson(
            release_groups,
            key=lambda item: (item.artist_mbid, item.mbid),
        ),
        RELEASES_FILE: _ndjson(
            releases,
            key=lambda item: (item.release_group_mbid, item.date or "", item.mbid),
        ),
        RECORDINGS_FILE: _ndjson(recordings, key=lambda item: (item.mbid,)),
        RELEASE_RECORDINGS_FILE: _ndjson(
            release_recordings,
            key=lambda item: (
                item.release_mbid,
                item.disc or "",
                item.position or "",
                item.track_number or "",
                item.recording_mbid,
            ),
        ),
        CREDITS_FILE: _ndjson(
            credits,
            key=lambda item: (
                item.scope,
                item.release_group_mbid or "",
                item.release_mbid or "",
                item.recording_mbid or "",
                item.artist_mbid,
                item.role,
                item.attributes,
            ),
        ),
        PLACES_FILE: _ndjson(
            places,
            key=lambda item: (
                item.scope,
                item.release_group_mbid or "",
                item.release_mbid or "",
                item.recording_mbid or "",
                item.place_mbid,
                item.relation_type,
            ),
        ),
        EXCLUSIONS_FILE: _ndjson(
            exclusions,
            key=lambda item: (item.release_group_mbid, item.reason),
        ),
    }


def _canonical_records(records: list[Any], *, key) -> list[Any]:
    grouped: dict[Any, list[Any]] = {}
    for record in records:
        grouped.setdefault(key(record), []).append(record)
    return [
        min(grouped[record_key], key=_record_token)
        for record_key in sorted(grouped, key=_key_token)
    ]


def _multi_artist_exclusions(
    release_groups: list[Any],
    excluded_group_mbids: set[str],
) -> list[ExclusionRecord]:
    grouped: dict[str, list[Any]] = {}
    for group in release_groups:
        if group.mbid in excluded_group_mbids:
            grouped.setdefault(group.mbid, []).append(group)
    exclusions: list[ExclusionRecord] = []
    for mbid in sorted(grouped):
        representative = min(grouped[mbid], key=_record_token)
        exclusions.append(
            ExclusionRecord(
                release_group_mbid=mbid,
                title=representative.title,
                primary_type=representative.primary_type,
                secondary_types=representative.secondary_types,
                first_release_date=representative.first_release_date,
                reason=MULTI_ARTIST_RELEASE_GROUP_REASON,
                raw_response_id=representative.raw_response_id,
            )
        )
    return exclusions


def _target_is_canonical(
    record: Any,
    *,
    group_mbids: set[str],
    release_mbids: set[str],
    recording_mbids: set[str],
) -> bool:
    if record.scope == "release_group":
        return record.release_group_mbid in group_mbids
    if record.scope == "release":
        return record.release_mbid in release_mbids
    if record.scope == "recording":
        return record.recording_mbid in recording_mbids
    return False


def _record_token(record: Any) -> str:
    return json.dumps(
        _jsonable(asdict(record)),
        sort_keys=True,
        separators=(",", ":"),
    )


def _key_token(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))


def _ndjson(records: list[Any], *, key) -> bytes:
    unique = sorted(
        set(records),
        key=lambda record: (_key_token(key(record)), _record_token(record)),
    )
    if not unique:
        return b""
    lines = [
        json.dumps(_jsonable(asdict(record)), sort_keys=True, separators=(",", ":"))
        for record in unique
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _dataset_version(
    files: dict[str, bytes],
    *,
    seed_list_version: str,
    taxonomy_version: str | None,
    period_start: date | str | None,
    period_end: date | str | None,
    batch_ids: Sequence[str],
    source_snapshot_at: datetime,
    code_version: str,
) -> str:
    digest = hashlib.sha256()
    context = {
        "seed_list_version": seed_list_version,
        "taxonomy_version": taxonomy_version,
        "period_start": _date_string(period_start),
        "period_end": _date_string(period_end),
        "batch_ids": sorted(batch_ids),
        "source_snapshot_at": source_snapshot_at.isoformat(),
        "code_version": code_version,
    }
    digest.update(json.dumps(context, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for name in sorted(files):
        digest.update(name.encode("utf-8"))
        digest.update(hashlib.sha256(files[name]).digest())
    timestamp = source_snapshot_at.strftime("%Y%m%dT%H%M%SZ")
    return f"mb-{timestamp}-{digest.hexdigest()[:12]}"


def _build_manifest(
    files: dict[str, bytes],
    extractions: list[BandExtraction],
    *,
    dataset_version: str,
    seed_list_version: str,
    taxonomy_version: str | None,
    period_start: date | str | None,
    period_end: date | str | None,
    batch_ids: Sequence[str],
    source_snapshot_at: datetime,
    code_version: str,
) -> dict[str, Any]:
    file_entries = {
        name: {
            "count": _line_count(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for name, data in sorted(files.items())
    }
    return {
        "dataset_version": dataset_version,
        "seed_list_version": seed_list_version,
        "taxonomy_version": taxonomy_version,
        "period_start": _date_string(period_start),
        "period_end": _date_string(period_end),
        "batch_ids": sorted(batch_ids),
        "source_snapshot_at": source_snapshot_at.isoformat(),
        "code_version": code_version,
        "schema_version": SCHEMA_VERSION,
        "source": "musicbrainz",
        "api_version": MUSICBRAINZ_API_VERSION,
        "format": DATASET_FORMAT,
        "band_count": len({extraction.band_mbid for extraction in extractions}),
        "files": file_entries,
    }


def _line_count(data: bytes) -> int:
    if not data:
        return 0
    return data.count(b"\n")


def _date_string(value: date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return value
