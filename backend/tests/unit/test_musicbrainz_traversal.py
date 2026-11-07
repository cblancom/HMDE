from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from hmde.etl.musicbrainz.client import MusicBrainzResponse
from hmde.etl.musicbrainz.raw_store import hash_payload
from hmde.etl.musicbrainz.seed import SeedBand
from hmde.etl.musicbrainz.traversal import (
    MusicBrainzTraversal,
    date_precision,
    release_group_exclusion_reason,
)
from hmde.models import RawResponse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "musicbrainz"
ARTIST = "11111111-1111-4111-8111-111111111111"
RG1 = "22222222-2222-4222-8222-222222222222"
RG2 = "33333333-3333-4333-8333-333333333333"
REL1 = "44444444-4444-4444-8444-444444444444"
REL2 = "55555555-5555-4555-8555-555555555555"
REC1 = "66666666-6666-4666-8666-666666666666"
REC2 = "77777777-7777-4777-8777-777777777777"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _response(data: dict) -> MusicBrainzResponse:
    body = json.dumps(data).encode("utf-8")
    raw = RawResponse(
        id=uuid.uuid4(),
        first_ingest_run_id=uuid.uuid4(),
        source="musicbrainz",
        source_entity_type="test",
        external_id="test",
        request_key="0" * 64,
        request_url="https://mb.test/ws/2/test",
        request_params={},
        fetched_at=datetime.now(UTC),
        http_status=200,
        payload_hash=hash_payload(body),
        raw_path="test.json",
        license="CC0-1.0",
        api_version="2",
    )
    return MusicBrainzResponse(data=data, raw_response=raw, from_cache=False)


class FakeClient:
    def __init__(self, handler: Callable[[str, dict], dict]) -> None:
        self.handler = handler
        self.calls: list[tuple[str, dict]] = []

    def fetch_json(self, path, *, params, source_entity_type, external_id):
        self.calls.append((path, dict(params)))
        return _response(self.handler(path, dict(params)))


def _handler(path: str, params: dict) -> dict:
    if path == f"artist/{ARTIST}":
        return _load("artist")
    if path == "release-group":
        return _load("release_groups")
    if path == "release":
        return _load("releases")
    if path == f"release/{REL1}":
        return _load("release_1")
    if path == f"release/{REL2}":
        return _load("release_2")
    if path == f"recording/{REC1}":
        return _load("recording_1")
    if path == f"recording/{REC2}":
        return _load("recording_2")
    raise AssertionError(f"unexpected MusicBrainz request: {path} {params}")


def _band() -> SeedBand:
    return SeedBand(
        name="Test Band",
        mbid=ARTIST,
        subgenre="Heavy Metal",
        country="GB",
        sequence=1,
    )


def test_extract_band_builds_entities_credits_places_and_exclusions() -> None:
    client = FakeClient(_handler)
    extraction = MusicBrainzTraversal(client).extract_band(_band())

    assert extraction.artist.name == "Test Band"
    assert extraction.artist.mbid == ARTIST
    assert extraction.external_ids[0].external_id == "Q12345"
    assert extraction.external_ids[0].source == "wikidata"

    assert len(extraction.release_groups) == 1
    assert extraction.release_groups[0].mbid == RG1
    assert extraction.release_groups[0].tags == ("heavy metal",)
    assert extraction.release_groups[0].date_precision == "day"

    assert len(extraction.exclusions) == 1
    assert extraction.exclusions[0].release_group_mbid == RG2
    assert extraction.exclusions[0].reason == "secondary_type"

    assert {release.mbid for release in extraction.releases} == {REL1, REL2}
    assert {recording.mbid for recording in extraction.recordings} == {REC1, REC2}
    assert len(extraction.release_recordings) == 3

    scopes = {credit.scope for credit in extraction.credits}
    assert scopes == {"release_group", "release", "recording"}
    release_group_credit = next(
        credit for credit in extraction.credits if credit.scope == "release_group"
    )
    assert release_group_credit.artist_name == "Producer One"
    assert release_group_credit.attributes == ("co",)
    assert release_group_credit.release_group_mbid == RG1
    recording_credits = {
        credit.role for credit in extraction.credits if credit.scope == "recording"
    }
    assert recording_credits == {"engineer", "mix"}

    assert {place.relation_type for place in extraction.places} == {
        "mixed at",
        "recorded at",
    }
    assert all(record.raw_response_id for record in extraction.release_groups)
    assert all(place.raw_response_id for place in extraction.places)


def test_unique_recordings_are_fetched_once() -> None:
    client = FakeClient(_handler)
    MusicBrainzTraversal(client).extract_band(_band())

    recording_calls = [path for path, _ in client.calls if path.startswith("recording/")]
    assert recording_calls == [f"recording/{REC1}", f"recording/{REC2}"]


def test_release_group_browse_paginates() -> None:
    groups = _load("release_groups")
    canonical = groups["release-groups"][0]
    excluded = groups["release-groups"][1]

    def handler(path: str, params: dict) -> dict:
        if path == "release-group":
            if params["offset"] == 0:
                return {
                    "release-groups": [canonical],
                    "release-group-count": 2,
                }
            return {
                "release-groups": [excluded],
                "release-group-count": 2,
            }
        return _handler(path, params)

    client = FakeClient(handler)
    extraction = MusicBrainzTraversal(client).extract_band(_band())

    assert [group.mbid for group in extraction.release_groups] == [RG1]
    assert [item.release_group_mbid for item in extraction.exclusions] == [RG2]
    offsets = [params["offset"] for path, params in client.calls if path == "release-group"]
    assert offsets == [0, 1]


@pytest.mark.parametrize(
    ("release_group", "reason"),
    [
        ({"primary-type": "Single", "secondary-types": []}, "not_album"),
        (
            {"primary-type": "Album", "secondary-types": ["Live"], "first-release-date": "1990"},
            "secondary_type",
        ),
        ({"primary-type": "Album", "secondary-types": []}, "missing_date"),
        (
            {"primary-type": "Album", "secondary-types": [], "first-release-date": "2001"},
            "out_of_period",
        ),
        (
            {"primary-type": "Album", "secondary-types": [], "first-release-date": "1979"},
            "out_of_period",
        ),
    ],
)
def test_release_group_exclusion_reason(release_group: dict, reason: str) -> None:
    assert release_group_exclusion_reason(release_group) == reason


def test_date_precision() -> None:
    assert date_precision("1985-05-01") == "day"
    assert date_precision("1985-05") == "month"
    assert date_precision("1985") == "year"
    assert date_precision(None) == "unknown"


@pytest.mark.parametrize(
    ("release_date", "period_start", "period_end", "reason"),
    [
        ("1959", 1960, 2026, "out_of_period"),
        ("1960", 1960, 2026, None),
        ("1975", 1960, 2026, None),
        ("2000", 1960, 2026, None),
        ("2026", 1960, 2026, None),
        ("2027", 1960, 2026, "out_of_period"),
    ],
)
def test_release_group_exclusion_uses_configured_period(
    release_date: str,
    period_start: int,
    period_end: int,
    reason: str | None,
) -> None:
    release_group = {
        "primary-type": "Album",
        "secondary-types": [],
        "first-release-date": release_date,
    }

    assert (
        release_group_exclusion_reason(
            release_group,
            period_start_year=period_start,
            period_end_year=period_end,
        )
        == reason
    )


def test_traversal_includes_albums_from_the_configured_expanded_period() -> None:
    groups = _load("release_groups")
    groups["release-groups"][0]["first-release-date"] = "1969-01-12"

    def handler(path: str, params: dict) -> dict:
        if path == "release-group":
            return groups
        return _handler(path, params)

    extraction = MusicBrainzTraversal(
        FakeClient(handler),
        period_start_year=1960,
        period_end_year=2026,
    ).extract_band(_band())

    assert [group.mbid for group in extraction.release_groups] == [RG1]
    assert all(exclusion.release_group_mbid != RG1 for exclusion in extraction.exclusions)


def test_browse_payload_with_recordings_avoids_lookup_requests() -> None:
    release_one = _load("release_1")
    release_two = _load("release_2")
    recording_relations = {
        REC1: _load("recording_1")["relations"],
        REC2: _load("recording_2")["relations"],
    }
    for release in (release_one, release_two):
        for medium in release.get("media", []):
            for track in medium.get("tracks", []):
                recording = track.get("recording") or {}
                if recording.get("id") in recording_relations:
                    recording["relations"] = recording_relations[recording["id"]]

    release_page = {
        "releases": [release_one, release_two],
        "release-count": 2,
        "release-offset": 0,
    }

    def handler(path: str, params: dict) -> dict:
        if path == f"artist/{ARTIST}":
            return _load("artist")
        if path == "release-group":
            return _load("release_groups")
        if path == "release":
            return release_page
        raise AssertionError(f"unexpected lookup request: {path}")

    client = FakeClient(handler)
    extraction = MusicBrainzTraversal(client).extract_band(_band())

    assert [path for path, _ in client.calls] == [
        f"artist/{ARTIST}",
        "release-group",
        "release",
    ]
    assert len(extraction.releases) == 2
    assert len(extraction.recordings) == 2
    assert len(extraction.release_recordings) == 3
    assert {credit.scope for credit in extraction.credits} == {
        "release_group",
        "release",
        "recording",
    }
    assert len(extraction.places) == 2
