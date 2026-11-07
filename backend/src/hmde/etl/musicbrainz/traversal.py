"""MusicBrainz entity traversal and credit extraction."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from hmde.etl.musicbrainz.client import MusicBrainzClient, MusicBrainzResponse
from hmde.etl.musicbrainz.seed import SeedBand

PERIOD_START_YEAR = 1980
PERIOD_END_YEAR = 2000
PRODUCTION_ROLES = {
    "producer",
    "co-producer",
    "executive producer",
    "assistant producer",
    "additional producer",
    "engineer",
    "mix",
    "mastering",
}
PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class ExtractedArtist:
    mbid: str
    name: str
    sort_name: str | None
    type: str | None
    country: str | None
    disambiguation: str | None
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class ExternalIdRecord:
    entity_type: str
    entity_mbid: str
    source: str
    external_id: str
    url: str
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class ReleaseGroupRecord:
    mbid: str
    artist_mbid: str
    title: str
    primary_type: str
    secondary_types: tuple[str, ...]
    first_release_date: str | None
    date_precision: str
    disambiguation: str | None
    tags: tuple[str, ...]
    genres: tuple[str, ...]
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    mbid: str
    release_group_mbid: str
    title: str
    date: str | None
    country: str | None
    status: str | None
    disambiguation: str | None
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class RecordingRecord:
    mbid: str
    title: str
    first_release_date: str | None
    disambiguation: str | None
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class ReleaseRecordingRecord:
    release_mbid: str
    recording_mbid: str
    disc: str | None
    position: str | None
    track_number: str | None
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class CreditRecord:
    scope: str
    artist_mbid: str
    artist_name: str
    role: str
    attributes: tuple[str, ...]
    release_group_mbid: str | None
    release_mbid: str | None
    recording_mbid: str | None
    credited_as: str | None
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class PlaceRelationshipRecord:
    relation_type: str
    scope: str
    place_mbid: str
    place_name: str
    release_group_mbid: str | None
    release_mbid: str | None
    recording_mbid: str | None
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class ExclusionRecord:
    release_group_mbid: str
    title: str
    primary_type: str
    secondary_types: tuple[str, ...]
    first_release_date: str | None
    reason: str
    raw_response_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class BandExtraction:
    band_mbid: str
    subgenre: str
    artist: ExtractedArtist
    external_ids: tuple[ExternalIdRecord, ...]
    release_groups: tuple[ReleaseGroupRecord, ...]
    releases: tuple[ReleaseRecord, ...]
    recordings: tuple[RecordingRecord, ...]
    release_recordings: tuple[ReleaseRecordingRecord, ...]
    credits: tuple[CreditRecord, ...]
    places: tuple[PlaceRelationshipRecord, ...]
    exclusions: tuple[ExclusionRecord, ...]


def date_precision(value: str | None) -> str:
    if not isinstance(value, str) or not value.strip():
        return "unknown"
    parts = value.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return "day"
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        return "month"
    if len(parts) == 1 and parts[0].isdigit():
        return "year"
    return "unknown"


def release_group_exclusion_reason(release_group: dict[str, Any]) -> str | None:
    primary_type = str(release_group.get("primary-type") or "").casefold()
    if primary_type != "album":
        return "not_album"
    if release_group.get("secondary-types"):
        return "secondary_type"
    year = _year(release_group.get("first-release-date"))
    if year is None:
        return "missing_date"
    if year < PERIOD_START_YEAR or year > PERIOD_END_YEAR:
        return "out_of_period"
    return None


class MusicBrainzTraversal:
    def __init__(self, client: MusicBrainzClient) -> None:
        self._client = client

    def extract_band(self, band: SeedBand) -> BandExtraction:
        artist_response = self._client.fetch_json(
            f"artist/{band.mbid}",
            params={"inc": "url-rels"},
            source_entity_type="artist",
            external_id=band.mbid,
        )
        artist_data = artist_response.data
        artist = ExtractedArtist(
            mbid=str(artist_data.get("id") or band.mbid),
            name=str(artist_data.get("name") or band.name),
            sort_name=_optional_string(artist_data.get("sort-name")),
            type=_optional_string(artist_data.get("type")),
            country=_optional_string(artist_data.get("country")),
            disambiguation=_optional_string(artist_data.get("disambiguation")),
            raw_response_id=artist_response.raw_response.id,
        )
        external_ids = self._extract_external_ids(artist.mbid, artist_response)
        release_groups, exclusions, group_credits, group_places = self._extract_release_groups(
            band, artist.mbid
        )
        releases: list[ReleaseRecord] = []
        recordings: dict[str, RecordingRecord] = {}
        recording_payloads: dict[str, tuple[dict[str, Any], uuid.UUID]] = {}
        release_recordings: list[ReleaseRecordingRecord] = []
        credits: list[CreditRecord] = list(group_credits)
        places: list[PlaceRelationshipRecord] = list(group_places)

        for group in release_groups:
            group_releases = self._browse(
                "release",
                {
                    "release-group": group.mbid,
                    "inc": ("recordings+recording-level-rels+artist-rels+place-rels"),
                },
                "releases",
                "release-count",
                "release",
                group.mbid,
            )
            for release_summary, browse_raw_response_id in group_releases:
                release_mbid = _required_id(release_summary)
                release_data = release_summary
                release_raw_response_id = browse_raw_response_id
                release_from_browse = isinstance(release_data.get("media"), list)
                if not release_from_browse:
                    release_response = self._client.fetch_json(
                        f"release/{release_mbid}",
                        params={"inc": "recordings+artist-rels+place-rels"},
                        source_entity_type="release",
                        external_id=release_mbid,
                    )
                    release_data = release_response.data
                    release_raw_response_id = release_response.raw_response.id
                release = ReleaseRecord(
                    mbid=str(release_data.get("id") or release_mbid),
                    release_group_mbid=group.mbid,
                    title=str(release_data.get("title") or release_summary.get("title") or ""),
                    date=_optional_string(release_data.get("date") or release_summary.get("date")),
                    country=_optional_string(
                        release_data.get("country") or release_summary.get("country")
                    ),
                    status=_optional_string(
                        release_data.get("status") or release_summary.get("status")
                    ),
                    disambiguation=_optional_string(
                        release_data.get("disambiguation") or release_summary.get("disambiguation")
                    ),
                    raw_response_id=release_raw_response_id,
                )
                releases.append(release)
                credits.extend(
                    _artist_credits(
                        release_data.get("relations", []),
                        scope="release",
                        raw_response_id=release_raw_response_id,
                        release_group_mbid=group.mbid,
                        release_mbid=release.mbid,
                    )
                )
                places.extend(
                    _place_relationships(
                        release_data.get("relations", []),
                        scope="release",
                        raw_response_id=release_raw_response_id,
                        release_group_mbid=group.mbid,
                        release_mbid=release.mbid,
                    )
                )

                for medium in release_data.get("media", []):
                    disc = _optional_string(medium.get("position"))
                    for track in medium.get("tracks", []):
                        recording_data = track.get("recording") or {}
                        recording_mbid = _optional_string(recording_data.get("id"))
                        if not recording_mbid:
                            continue
                        recordings.setdefault(
                            recording_mbid,
                            RecordingRecord(
                                mbid=recording_mbid,
                                title=str(recording_data.get("title") or track.get("title") or ""),
                                first_release_date=_optional_string(
                                    recording_data.get("first-release-date")
                                ),
                                disambiguation=_optional_string(
                                    recording_data.get("disambiguation")
                                ),
                                raw_response_id=release_raw_response_id,
                            ),
                        )
                        if release_from_browse:
                            recording_payloads.setdefault(
                                recording_mbid,
                                (recording_data, release_raw_response_id),
                            )
                        release_recordings.append(
                            ReleaseRecordingRecord(
                                release_mbid=release.mbid,
                                recording_mbid=recording_mbid,
                                disc=disc,
                                position=_optional_string(track.get("position")),
                                track_number=_optional_string(track.get("number")),
                                raw_response_id=release_raw_response_id,
                            )
                        )

        final_recordings: list[RecordingRecord] = []
        for recording_mbid in sorted(recordings):
            fallback = recordings[recording_mbid]
            payload = recording_payloads.get(recording_mbid)
            if payload is not None and "relations" in payload[0]:
                recording_data, recording_raw_response_id = payload
            else:
                recording_response = self._client.fetch_json(
                    f"recording/{recording_mbid}",
                    params={"inc": "artist-rels+place-rels"},
                    source_entity_type="recording",
                    external_id=recording_mbid,
                )
                recording_data = recording_response.data
                recording_raw_response_id = recording_response.raw_response.id
            recording = RecordingRecord(
                mbid=str(recording_data.get("id") or recording_mbid),
                title=str(recording_data.get("title") or fallback.title),
                first_release_date=_optional_string(
                    recording_data.get("first-release-date") or fallback.first_release_date
                ),
                disambiguation=_optional_string(
                    recording_data.get("disambiguation") or fallback.disambiguation
                ),
                raw_response_id=recording_raw_response_id,
            )
            final_recordings.append(recording)
            credits.extend(
                _artist_credits(
                    recording_data.get("relations", []),
                    scope="recording",
                    raw_response_id=recording_raw_response_id,
                    recording_mbid=recording.mbid,
                )
            )
            places.extend(
                _place_relationships(
                    recording_data.get("relations", []),
                    scope="recording",
                    raw_response_id=recording_raw_response_id,
                    recording_mbid=recording.mbid,
                )
            )

        return BandExtraction(
            band_mbid=band.mbid,
            subgenre=band.subgenre,
            artist=artist,
            external_ids=tuple(external_ids),
            release_groups=tuple(release_groups),
            releases=tuple(releases),
            recordings=tuple(final_recordings),
            release_recordings=tuple(release_recordings),
            credits=tuple(credits),
            places=tuple(places),
            exclusions=tuple(exclusions),
        )

    def _extract_external_ids(
        self,
        artist_mbid: str,
        response: MusicBrainzResponse,
    ) -> list[ExternalIdRecord]:
        external_ids: list[ExternalIdRecord] = []
        for relation in response.data.get("relations", []):
            if relation.get("target-type") != "url":
                continue
            url = str((relation.get("url") or {}).get("resource") or "")
            if relation.get("type") != "wikidata" and "wikidata.org/wiki/Q" not in url:
                continue
            qid = url.rstrip("/").rsplit("/", 1)[-1]
            if not qid.startswith("Q"):
                continue
            external_ids.append(
                ExternalIdRecord(
                    entity_type="artist",
                    entity_mbid=artist_mbid,
                    source="wikidata",
                    external_id=qid,
                    url=url,
                    raw_response_id=response.raw_response.id,
                )
            )
        return external_ids

    def _extract_release_groups(
        self,
        band: SeedBand,
        artist_mbid: str,
    ) -> tuple[
        list[ReleaseGroupRecord],
        list[ExclusionRecord],
        list[CreditRecord],
        list[PlaceRelationshipRecord],
    ]:
        groups: list[ReleaseGroupRecord] = []
        exclusions: list[ExclusionRecord] = []
        credits: list[CreditRecord] = []
        places: list[PlaceRelationshipRecord] = []
        items = self._browse(
            "release-group",
            {
                "artist": band.mbid,
                "type": "album",
                "inc": "artist-rels+place-rels+genres+tags",
            },
            "release-groups",
            "release-group-count",
            "release-group",
            artist_mbid,
        )
        for data, raw_response_id in items:
            mbid = _required_id(data)
            reason = release_group_exclusion_reason(data)
            if reason is not None:
                exclusions.append(
                    ExclusionRecord(
                        release_group_mbid=mbid,
                        title=str(data.get("title") or ""),
                        primary_type=str(data.get("primary-type") or ""),
                        secondary_types=tuple(
                            str(item) for item in data.get("secondary-types") or []
                        ),
                        first_release_date=_optional_string(data.get("first-release-date")),
                        reason=reason,
                        raw_response_id=raw_response_id,
                    )
                )
                continue
            groups.append(
                ReleaseGroupRecord(
                    mbid=mbid,
                    artist_mbid=artist_mbid,
                    title=str(data.get("title") or ""),
                    primary_type=str(data.get("primary-type") or ""),
                    secondary_types=tuple(str(item) for item in data.get("secondary-types") or []),
                    first_release_date=_optional_string(data.get("first-release-date")),
                    date_precision=date_precision(_optional_string(data.get("first-release-date"))),
                    disambiguation=_optional_string(data.get("disambiguation")),
                    tags=_names(data.get("tags")),
                    genres=_names(data.get("genres")),
                    raw_response_id=raw_response_id,
                )
            )
            credits.extend(
                _artist_credits(
                    data.get("relations", []),
                    scope="release_group",
                    raw_response_id=raw_response_id,
                    release_group_mbid=mbid,
                )
            )
            places.extend(
                _place_relationships(
                    data.get("relations", []),
                    scope="release_group",
                    raw_response_id=raw_response_id,
                    release_group_mbid=mbid,
                )
            )
        return groups, exclusions, credits, places

    def _browse(
        self,
        path: str,
        params: dict[str, Any],
        collection_key: str,
        count_key: str,
        source_entity_type: str,
        external_id: str,
    ) -> list[tuple[dict[str, Any], uuid.UUID]]:
        items: list[tuple[dict[str, Any], uuid.UUID]] = []
        offset = 0
        while True:
            response = self._client.fetch_json(
                path,
                params={**params, "limit": PAGE_SIZE, "offset": offset},
                source_entity_type=source_entity_type,
                external_id=external_id,
            )
            page = response.data.get(collection_key)
            if not isinstance(page, list):
                break
            items.extend((item, response.raw_response.id) for item in page)
            total = _as_int(response.data.get(count_key), default=offset + len(page))
            offset += len(page)
            if not page or offset >= total:
                break
        return items


def _artist_credits(
    relations: list[dict[str, Any]],
    *,
    scope: str,
    raw_response_id: uuid.UUID,
    release_group_mbid: str | None = None,
    release_mbid: str | None = None,
    recording_mbid: str | None = None,
) -> list[CreditRecord]:
    credits: list[CreditRecord] = []
    for relation in relations:
        if relation.get("target-type") != "artist":
            continue
        role = str(relation.get("type") or "").casefold()
        if role not in PRODUCTION_ROLES:
            continue
        artist = relation.get("artist") or {}
        artist_mbid = _optional_string(artist.get("id"))
        artist_name = _optional_string(artist.get("name"))
        if not artist_mbid or not artist_name:
            continue
        attributes = tuple(
            sorted(
                {
                    str(attribute).casefold()
                    for attribute in relation.get("attributes") or []
                    if str(attribute).strip()
                }
            )
        )
        credited_as = _optional_string(relation.get("target-credit")) or _optional_string(
            relation.get("source-credit")
        )
        credits.append(
            CreditRecord(
                scope=scope,
                artist_mbid=artist_mbid,
                artist_name=artist_name,
                role=role,
                attributes=attributes,
                release_group_mbid=release_group_mbid,
                release_mbid=release_mbid,
                recording_mbid=recording_mbid,
                credited_as=credited_as,
                raw_response_id=raw_response_id,
            )
        )
    return credits


def _place_relationships(
    relations: list[dict[str, Any]],
    *,
    scope: str,
    raw_response_id: uuid.UUID,
    release_group_mbid: str | None = None,
    release_mbid: str | None = None,
    recording_mbid: str | None = None,
) -> list[PlaceRelationshipRecord]:
    places: list[PlaceRelationshipRecord] = []
    for relation in relations:
        if relation.get("target-type") != "place":
            continue
        place = relation.get("place") or {}
        place_mbid = _optional_string(place.get("id"))
        place_name = _optional_string(place.get("name"))
        if not place_mbid or not place_name:
            continue
        places.append(
            PlaceRelationshipRecord(
                relation_type=str(relation.get("type") or "").casefold(),
                scope=scope,
                place_mbid=place_mbid,
                place_name=place_name,
                release_group_mbid=release_group_mbid,
                release_mbid=release_mbid,
                recording_mbid=recording_mbid,
                raw_response_id=raw_response_id,
            )
        )
    return places


def _names(values: object) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    names = {
        str(item.get("name")).strip()
        for item in values
        if isinstance(item, dict) and item.get("name")
    }
    return tuple(sorted(names))


def _year(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    first = value.split("-", 1)[0]
    if not first.isdigit():
        return None
    return int(first)


def _as_int(value: object, *, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _required_id(payload: dict[str, Any]) -> str:
    mbid = _optional_string(payload.get("id"))
    if not mbid:
        raise ValueError("MusicBrainz entity is missing an id")
    return mbid
