from __future__ import annotations

import hashlib
import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "e2"


def load(name: str):
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_manifest_counts_and_checksums() -> None:
    manifest = load("manifest")
    release_groups = load("release_groups")
    credits = load("credits")

    assert manifest["version"] == "e2-v0.1.0"
    assert manifest["band_count"] == 14
    assert set(manifest["subgenre_distribution"].values()) == {2}
    assert all(2 <= band["album_count"] <= 3 for band in manifest["bands"])
    assert all(band["producer_credit_count"] >= 1 for band in manifest["bands"])
    assert manifest["album_count"] == len(release_groups)
    assert manifest["credit_count"] == len(credits)

    for name, expected in manifest["files"].items():
        actual = hashlib.sha256((FIXTURE_DIR / name).read_bytes()).hexdigest()
        assert actual == expected


def test_fixture_references_are_consistent() -> None:
    source_records = {row["id"] for row in load("source_records")}
    artists = {row["id"]: row for row in load("artists")}
    release_groups = {row["id"]: row for row in load("release_groups")}
    releases = {row["id"]: row for row in load("releases")}
    recordings = {row["id"]: row for row in load("recordings")}
    roles = {row["code"] for row in load("roles")}
    subgenres = {row["code"] for row in load("subgenres")}

    for artist in artists.values():
        assert artist["source_record_id"] in source_records

    for group in release_groups.values():
        assert group["artist_id"] in artists
        assert group["source_record_id"] in source_records

    for release in releases.values():
        assert release["release_group_id"] in release_groups
        assert release["source_record_id"] in source_records

    for recording in recordings.values():
        assert recording["source_record_id"] in source_records

    for link in load("recording_releases"):
        assert link["release_id"] in releases
        assert link["recording_id"] in recordings

    for link in load("artist_subgenres"):
        assert link["artist_id"] in artists
        assert link["subgenre_code"] in subgenres
        assert link["source_record_id"] in source_records

    for external_id in load("external_ids"):
        assert external_id["entity_id"] in artists

    for credit in load("credits"):
        assert credit["artist_id"] in artists
        assert credit["role_code"] in roles
        assert credit["release_group_id"] in release_groups
        assert credit["source_record_id"] in source_records
        if credit["scope"] == "release":
            assert credit["release_id"] in releases
            assert credit["recording_id"] is None
        elif credit["scope"] == "recording":
            assert credit["recording_id"] in recordings
        else:
            assert credit["scope"] == "release_group"
            assert credit["release_id"] is None
            assert credit["recording_id"] is None


def test_every_band_has_a_producer_credit() -> None:
    artists = {row["id"]: row for row in load("artists")}
    release_groups = load("release_groups")
    credits = load("credits")
    groups_by_id = {row["id"]: row for row in release_groups}
    core_roles = {"producer", "co-producer"}

    band_names = {
        "Iron Maiden",
        "Judas Priest",
        "Metallica",
        "Slayer",
        "Death",
        "Cannibal Corpse",
        "Bathory",
        "Mayhem",
        "Helloween",
        "Blind Guardian",
        "Candlemass",
        "Paradise Lost",
        "Dream Theater",
        "Fates Warning",
    }
    band_ids = {
        artist["id"]
        for artist in artists.values()
        if artist["name"] in band_names and artist["type"] == "group"
    }

    assert len(band_ids) == 14

    for band_id in band_ids:
        album_ids = {group["id"] for group in release_groups if group["artist_id"] == band_id}
        assert 2 <= len(album_ids) <= 3
        assert any(
            credit["release_group_id"] in album_ids and credit["role_code"] in core_roles
            for credit in credits
        ), artists[band_id]["name"]
        assert all(group_id in groups_by_id for group_id in album_ids)
