"""Versioned extracted dataset writer."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hmde.etl.musicbrainz.traversal import BandExtraction

SCHEMA_VERSION = "1"
MUSICBRAINZ_API_VERSION = "2"
DATASET_FORMAT = "ndjson"

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
    source_snapshot_at: datetime,
    code_version: str,
) -> DatasetWriteResult:
    extraction_list = list(extractions)
    files = _build_files(extraction_list)
    source_snapshot = source_snapshot_at.astimezone(UTC)
    dataset_version = _dataset_version(
        files,
        seed_list_version=seed_list_version,
        source_snapshot_at=source_snapshot,
        code_version=code_version,
    )
    manifest = _build_manifest(
        files,
        extraction_list,
        dataset_version=dataset_version,
        seed_list_version=seed_list_version,
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
    artists = [extraction.artist for extraction in extractions]
    external_ids = [item for extraction in extractions for item in extraction.external_ids]
    release_groups = [item for extraction in extractions for item in extraction.release_groups]
    releases = [item for extraction in extractions for item in extraction.releases]
    recordings = [item for extraction in extractions for item in extraction.recordings]
    release_recordings = [
        item for extraction in extractions for item in extraction.release_recordings
    ]
    credits = [item for extraction in extractions for item in extraction.credits]
    places = [item for extraction in extractions for item in extraction.places]
    exclusions = [item for extraction in extractions for item in extraction.exclusions]

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
                str(item.raw_response_id),
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
                str(item.raw_response_id),
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
                str(item.raw_response_id),
            ),
        ),
        EXCLUSIONS_FILE: _ndjson(
            exclusions,
            key=lambda item: (
                item.release_group_mbid,
                item.reason,
                str(item.raw_response_id),
            ),
        ),
    }


def _ndjson(records: list[Any], *, key) -> bytes:
    unique = sorted(set(records), key=key)
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
    source_snapshot_at: datetime,
    code_version: str,
) -> str:
    digest = hashlib.sha256()
    context = {
        "seed_list_version": seed_list_version,
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
