"""Credit, role and recording-context normalization."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import Artist, Credit

from .entities import EntityIndex, read_ndjson
from .errors import InputValidationError
from .ids import stable_uuid
from .inputs import NormalizationInputs

PRODUCER_ATTRIBUTES = {
    "co": "co-producer",
    "executive": "executive-producer",
    "assistant": "assistant-producer",
    "additional": "additional-producer",
}
PASSTHROUGH_ROLES = {"engineer", "mix", "mastering"}
VALID_SCOPES = {"release_group", "release", "recording"}


@dataclass(frozen=True, slots=True)
class QuarantinedCredit:
    source_key: str
    reason: str
    record: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CreditCounts:
    source_credits: int
    artists_created: int
    created: int
    reused: int
    expanded_contexts: int
    quarantined: int


@dataclass(frozen=True, slots=True)
class CreditNormalizationResult:
    counts: CreditCounts
    quarantined: tuple[QuarantinedCredit, ...]


def normalize_role(role: str, attributes: list[str]) -> str | None:
    normalized_role = role.casefold().strip()
    normalized_attributes = {item.casefold().strip() for item in attributes}
    if normalized_role == "producer":
        for attribute, role_code in PRODUCER_ATTRIBUTES.items():
            if attribute in normalized_attributes:
                return role_code
        return "producer"
    if normalized_role in PASSTHROUGH_ROLES:
        return normalized_role
    return None


def normalize_credits(
    session: Session,
    inputs: NormalizationInputs,
    index: EntityIndex,
) -> CreditNormalizationResult:
    rows = read_ndjson(inputs.dataset.file("credits.ndjson").path)
    created = reused = expanded = artists_created = 0
    quarantined: list[QuarantinedCredit] = []
    artist_ids = dict(index.artists)
    credit_artist_mbids = {
        mbid
        for row in rows
        if (mbid := _optional_mbid(row.get("artist_mbid"))) is not None and mbid not in artist_ids
    }
    existing_artists = {
        row.mbid: row
        for row in session.scalars(select(Artist).where(Artist.mbid.in_(credit_artist_mbids)))
    }
    for mbid, artist in existing_artists.items():
        artist_ids[mbid] = artist.id

    for position, row in enumerate(rows, start=1):
        source_key = f"credit:{position}"
        artist_mbid = _optional_mbid(row.get("artist_mbid"))
        role = _string(row.get("role"))
        attributes = _attributes(row.get("attributes"))
        scope = _string(row.get("scope"))
        if artist_mbid is None:
            quarantined.append(QuarantinedCredit(source_key, "missing or invalid artist MBID", row))
            continue
        source_id = _source_id(row, index)
        if source_id is None:
            quarantined.append(QuarantinedCredit(source_key, "missing source provenance", row))
            continue
        artist_id = artist_ids.get(artist_mbid)
        if artist_id is None:
            artist_id = stable_uuid("artist", artist_mbid)
            artist = Artist(
                id=artist_id,
                mbid=artist_mbid,
                name=_required_artist_name(row),
                sort_name=_required_artist_name(row),
                type="other",
                country=None,
                disambiguation=None,
                source_record_id=source_id,
            )
            session.add(artist)
            artist_ids[artist_mbid] = artist_id
            artists_created += 1
        role_code = normalize_role(role, attributes)
        if role_code is None:
            quarantined.append(QuarantinedCredit(source_key, "unmapped role", row))
            continue
        if scope not in VALID_SCOPES:
            quarantined.append(QuarantinedCredit(source_key, "invalid credit scope", row))
            continue
        contexts = _contexts(row, scope, index)
        if not contexts:
            quarantined.append(
                QuarantinedCredit(source_key, "missing canonical album context", row)
            )
            continue
        if len(contexts) > 1:
            expanded += 1

        for group_id, release_id, recording_id in contexts:
            key = "|".join(
                (
                    artist_mbid,
                    role_code,
                    scope,
                    str(group_id),
                    str(release_id or ""),
                    str(recording_id or ""),
                    json.dumps(sorted(attributes), separators=(",", ":")),
                    str(source_id),
                )
            )
            credit_id = stable_uuid("credit", key)
            credit = session.get(Credit, credit_id)
            if credit is None:
                credit = Credit(
                    id=credit_id,
                    artist_id=artist_id,
                    role_code=role_code,
                    scope=scope,
                    release_group_id=group_id,
                    release_id=release_id,
                    recording_id=recording_id,
                    source_record_id=source_id,
                    confidence=1.0,
                    status="confirmed",
                    credited_as=_optional(row.get("credited_as")),
                    attributes={
                        "source_role": role,
                        "source_attributes": sorted(attributes),
                    },
                )
                session.add(credit)
                created += 1
            else:
                reused += 1

    session.flush()
    return CreditNormalizationResult(
        counts=CreditCounts(
            source_credits=len(rows),
            artists_created=artists_created,
            created=created,
            reused=reused,
            expanded_contexts=expanded,
            quarantined=len(quarantined),
        ),
        quarantined=tuple(quarantined),
    )


def _contexts(
    row: dict[str, Any],
    scope: str,
    index: EntityIndex,
) -> list[tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None]]:
    if scope == "release_group":
        group_id = _group_id(row, index)
        return [] if group_id is None else [(group_id, None, None)]
    if scope == "release":
        group_id = _group_id(row, index)
        release_id = index.releases.get(_optional_mbid(row.get("release_mbid")) or "")
        if group_id is None or release_id is None:
            return []
        return [(group_id, release_id, None)]
    recording_mbid = _optional_mbid(row.get("recording_mbid"))
    if recording_mbid is None:
        return []
    recording_id = index.recordings.get(recording_mbid)
    if recording_id is None:
        return []
    return [
        (group_id, None, recording_id)
        for group_id in sorted(index.recording_release_groups.get(recording_mbid, ()))
    ]


def _group_id(row: dict[str, Any], index: EntityIndex) -> uuid.UUID | None:
    group_mbid = _optional_mbid(row.get("release_group_mbid"))
    if group_mbid is None:
        return None
    return index.release_groups.get(group_mbid)


def _source_id(row: dict[str, Any], index: EntityIndex) -> uuid.UUID | None:
    raw_id = _optional_mbid(row.get("raw_response_id"))
    if raw_id is None:
        return None
    return index.source_records.get(uuid.UUID(raw_id))


def _required_artist_name(row: dict[str, Any]) -> str:
    value = row.get("artist_name")
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError("credit is missing a valid artist_name")
    return value.strip()


def _attributes(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


def _optional_mbid(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError as exc:
        raise InputValidationError(f"invalid credit MBID: {value!r}") from exc


def _string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError("credit is missing a required string field")
    return value.strip()


def _optional(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
