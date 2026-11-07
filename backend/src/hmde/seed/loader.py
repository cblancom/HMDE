"""Load the versioned E2 fixture dataset into PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from hmde.models import (
    Artist,
    ArtistSubgenre,
    Credit,
    ExternalId,
    FixtureLoad,
    Recording,
    RecordingRelease,
    Release,
    ReleaseGroup,
    Role,
    SourceRecord,
    Subgenre,
)

FIXTURE_FILES = {
    "artists": "artists",
    "artist_subgenres": "artist_subgenres",
    "credits": "credits",
    "external_ids": "external_ids",
    "recording_releases": "recording_releases",
    "recordings": "recordings",
    "release_groups": "release_groups",
    "releases": "releases",
    "roles": "roles",
    "source_records": "source_records",
    "subgenres": "subgenres",
}

COUNT_KEYS = {
    "artist_count": "artists",
    "artist_subgenre_count": "artist_subgenres",
    "credit_count": "credits",
    "external_id_count": "external_ids",
    "recording_release_count": "recording_releases",
    "recording_count": "recordings",
    "release_group_count": "release_groups",
    "release_count": "releases",
    "role_count": "roles",
    "source_record_count": "source_records",
    "subgenre_count": "subgenres",
}


@dataclass(frozen=True)
class FixtureLoadResult:
    version: str
    bands: int
    albums: int
    credits: int


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture_data(fixtures_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    manifest = _load_json(fixtures_dir / "manifest.json")
    data: dict[str, list[dict[str, Any]]] = {}
    for key, filename in FIXTURE_FILES.items():
        path = fixtures_dir / f"{filename}.json"
        data[key] = _load_json(path)

    manifest_files = manifest.get("files", {})
    for filename, expected in manifest_files.items():
        path = fixtures_dir / filename
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"fixture checksum mismatch: {filename}")

    for count_key, data_key in COUNT_KEYS.items():
        expected = manifest.get(count_key)
        if expected is not None and expected != len(data[data_key]):
            raise ValueError(
                f"fixture count mismatch for {count_key}: "
                f"manifest={expected}, file={len(data[data_key])}"
            )

    if manifest.get("album_count") != len(data["release_groups"]):
        raise ValueError("manifest album_count does not match release_groups")
    if manifest.get("credit_count") != len(data["credits"]):
        raise ValueError("manifest credit_count does not match credits")
    if manifest.get("band_count") != len(manifest.get("bands", [])):
        raise ValueError("manifest band_count does not match bands list")

    return manifest, data


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _date(value: str | None) -> date | None:
    if not value:
        return None
    if len(value) == 4 and value.isdigit():
        return date(int(value), 1, 1)
    if len(value) == 7 and value[4:5] == "-":
        return date(int(value[:4]), int(value[5:7]), 1)
    return date.fromisoformat(value)


def _merge_rows(
    session: Session,
    model: type[Any],
    rows: list[dict[str, Any]],
    mapper: Any,
) -> None:
    for row in rows:
        session.merge(model(**mapper(row)))
    session.flush()


def load_fixtures(fixtures_dir: Path, session: Session) -> FixtureLoadResult:
    manifest, data = load_fixture_data(fixtures_dir)

    _merge_rows(
        session,
        SourceRecord,
        data["source_records"],
        lambda row: {
            "id": _uuid(row["id"]),
            "source": row["source"],
            "source_entity_type": row["source_entity_type"],
            "external_id": row["external_id"],
            "source_url": row["source_url"],
            "fetched_at": _datetime(row["fetched_at"]),
            "license": row["license"],
            "payload_hash": row["payload_hash"],
            "fixture_version": row["fixture_version"],
        },
    )
    _merge_rows(
        session,
        Role,
        data["roles"],
        lambda row: {
            "code": row["code"],
            "name": row["name"],
            "category": row["category"],
        },
    )
    _merge_rows(
        session,
        Subgenre,
        data["subgenres"],
        lambda row: {
            "code": row["code"],
            "name": row["name"],
        },
    )
    _merge_rows(
        session,
        Artist,
        data["artists"],
        lambda row: {
            "id": _uuid(row["id"]),
            "mbid": row["mbid"],
            "name": row["name"],
            "sort_name": row["sort_name"],
            "type": row["type"],
            "country": row["country"],
            "disambiguation": row["disambiguation"],
            "source_record_id": _uuid(row["source_record_id"]),
        },
    )
    _merge_rows(
        session,
        ArtistSubgenre,
        data["artist_subgenres"],
        lambda row: {
            "artist_id": _uuid(row["artist_id"]),
            "subgenre_code": row["subgenre_code"],
            "is_primary": row["is_primary"],
            "confidence": row["confidence"],
            "source_record_id": _uuid(row["source_record_id"]),
        },
    )
    _merge_rows(
        session,
        ExternalId,
        data["external_ids"],
        lambda row: {
            "id": _uuid(row["id"]),
            "entity_type": row["entity_type"],
            "entity_id": _uuid(row["entity_id"]),
            "source": row["source"],
            "external_id": row["external_id"],
            "url": row["url"],
        },
    )
    _merge_rows(
        session,
        ReleaseGroup,
        data["release_groups"],
        lambda row: {
            "id": _uuid(row["id"]),
            "mbid": row["mbid"],
            "artist_id": _uuid(row["artist_id"]),
            "title": row["title"],
            "first_release_date": _date(row["first_release_date"]),
            "first_release_precision": row["first_release_precision"],
            "primary_type": row["primary_type"],
            "secondary_types": row["secondary_types"],
            "disambiguation": row["disambiguation"],
            "source_record_id": _uuid(row["source_record_id"]),
        },
    )
    _merge_rows(
        session,
        Release,
        data["releases"],
        lambda row: {
            "id": _uuid(row["id"]),
            "mbid": row["mbid"],
            "release_group_id": _uuid(row["release_group_id"]),
            "title": row["title"],
            "release_date": _date(row["release_date"]),
            "release_date_precision": row["release_date_precision"],
            "country": row["country"],
            "status": row["status"],
            "source_record_id": _uuid(row["source_record_id"]),
        },
    )
    _merge_rows(
        session,
        Recording,
        data["recordings"],
        lambda row: {
            "id": _uuid(row["id"]),
            "mbid": row["mbid"],
            "title": row["title"],
            "source_record_id": _uuid(row["source_record_id"]),
        },
    )
    _merge_rows(
        session,
        RecordingRelease,
        data["recording_releases"],
        lambda row: {
            "id": _uuid(row["id"]),
            "release_id": _uuid(row["release_id"]),
            "recording_id": _uuid(row["recording_id"]),
            "disc": row["disc"],
            "position": row["position"],
        },
    )
    _merge_rows(
        session,
        Credit,
        data["credits"],
        lambda row: {
            "id": _uuid(row["id"]),
            "artist_id": _uuid(row["artist_id"]),
            "role_code": row["role_code"],
            "scope": row["scope"],
            "release_group_id": _uuid(row["release_group_id"]),
            "release_id": _uuid(row["release_id"]) if row["release_id"] else None,
            "recording_id": _uuid(row["recording_id"]) if row["recording_id"] else None,
            "source_record_id": _uuid(row["source_record_id"]),
            "confidence": row["confidence"],
            "status": row["status"],
            "credited_as": row["credited_as"],
            "attributes": row["attributes"],
        },
    )

    fixture_load = FixtureLoad(
        id=uuid.uuid4(),
        version=manifest["version"],
        source="fixtures",
        band_count=manifest["band_count"],
        album_count=manifest["album_count"],
        credit_count=manifest["credit_count"],
    )
    session.add(fixture_load)
    session.flush()

    return FixtureLoadResult(
        version=manifest["version"],
        bands=manifest["band_count"],
        albums=manifest["album_count"],
        credits=manifest["credit_count"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()

    from hmde.db.session import SessionLocal

    if not args.fixtures.is_dir():
        raise SystemExit(f"fixtures directory not found: {args.fixtures}")

    with SessionLocal() as session:
        result = load_fixtures(args.fixtures, session)
        session.commit()

    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
