#!/usr/bin/env python3
"""Build the versioned E2 fixture dataset from the MusicBrainz spike cache.

This is a one-off development tool. It is not used by the API or the E2 loader.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

FIXTURE_VERSION = "e2-v0.1.0"
FIXTURE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://hmde.local/fixtures/e2")
SOURCE = "musicbrainz"
LICENSE = "CC0-1.0"

SUBGENRES = {
    "Heavy Metal": "heavy-metal",
    "Thrash Metal": "thrash-metal",
    "Death Metal": "death-metal",
    "Black Metal": "black-metal",
    "Power Metal": "power-metal",
    "Doom Metal": "doom-metal",
    "Progressive Metal": "progressive-metal",
}

BANDS = [
    ("Iron Maiden", "Heavy Metal"),
    ("Judas Priest", "Heavy Metal"),
    ("Metallica", "Thrash Metal"),
    ("Slayer", "Thrash Metal"),
    ("Death", "Death Metal"),
    ("Cannibal Corpse", "Death Metal"),
    ("Bathory", "Black Metal"),
    ("Mayhem", "Black Metal"),
    ("Helloween", "Power Metal"),
    ("Blind Guardian", "Power Metal"),
    ("Candlemass", "Doom Metal"),
    ("Paradise Lost", "Doom Metal"),
    ("Dream Theater", "Progressive Metal"),
    ("Fates Warning", "Progressive Metal"),
]

ROLE_DEFINITIONS = {
    "producer": ("Producer", "core"),
    "co-producer": ("Co-producer", "core"),
    "executive-producer": ("Executive producer", "extended"),
    "assistant-producer": ("Assistant producer", "extended"),
    "additional-producer": ("Additional producer", "extended"),
    "engineer": ("Engineer", "extended"),
    "mix": ("Mix", "extended"),
    "mastering": ("Mastering", "extended"),
}


def stable_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(FIXTURE_NAMESPACE, f"{kind}:{value}"))


def hash_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def date_precision(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) >= 10 and value[4:5] == "-" and value[7:8] == "-":
        return "day"
    if len(value) == 7 and value[4:5] == "-":
        return "month"
    if len(value) == 4 and value.isdigit():
        return "year"
    return None


def map_role(relation: dict[str, Any]) -> tuple[str, str, str] | None:
    relation_type = str(relation.get("type", "")).casefold()
    attributes = {str(attribute).casefold() for attribute in relation.get("attributes", [])}

    if relation_type == "producer":
        if "co" in attributes:
            code = "co-producer"
        elif "executive" in attributes:
            code = "executive-producer"
        elif "assistant" in attributes:
            code = "assistant-producer"
        elif "additional" in attributes:
            code = "additional-producer"
        else:
            code = "producer"
    elif relation_type in {"engineer", "mix", "mastering"}:
        code = relation_type
    else:
        return None

    name, category = ROLE_DEFINITIONS[code]
    return code, name, category


def is_production_relation(relation: dict[str, Any]) -> bool:
    return relation.get("target-type") == "artist" and map_role(relation) is not None


def has_production_relation(release: dict[str, Any]) -> bool:
    return any(is_production_relation(relation) for relation in release.get("relations", []))


def has_core_producer_relation(relations: list[dict[str, Any]]) -> bool:
    for relation in relations:
        role = map_role(relation)
        if role and role[0] in {"producer", "co-producer"}:
            return True
    return False


def choose_original_release(releases: list[dict[str, Any]]) -> dict[str, Any]:
    if not releases:
        raise ValueError("album has no cached releases")
    official = [release for release in releases if release.get("status") == "Official"]
    candidates = official or releases
    earliest = min(candidates, key=release_sort_key)
    if has_production_relation(earliest):
        return earliest
    with_credits = [release for release in candidates if has_production_relation(release)]
    return min(with_credits, key=release_sort_key) if with_credits else earliest


def album_has_core_producer(
    album: dict[str, Any],
    releases_by_group: dict[str, list[dict[str, Any]]],
    recording_releases: dict[str, dict[str, Any]],
) -> bool:
    group_id = album["release_group_id"]
    releases = releases_by_group.get(group_id, [])
    if releases and has_core_producer_relation(
        choose_original_release(releases).get("relations", [])
    ):
        return True

    recording_release_id = album.get("recording_credit_release_id")
    recording_entry = recording_releases.get(recording_release_id)
    if not recording_entry:
        return False

    data = recording_entry["data"]
    for medium in data.get("media", []):
        for track in medium.get("tracks", []):
            recording = track.get("recording") or {}
            if has_core_producer_relation(recording.get("relations", [])):
                return True
    return False


def release_sort_key(release: dict[str, Any]) -> tuple[str, str]:
    return (release.get("date") or "9999-99-99", release.get("id", ""))


def choose_credit_release(releases: list[dict[str, Any]]) -> dict[str, Any]:
    return choose_original_release(releases)


def choose_albums(
    result: dict[str, Any],
    releases_by_group: dict[str, list[dict[str, Any]]],
    recording_releases: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = [
        album
        for album in result.get("albums", [])
        if not album.get("low_confidence") and album.get("first_release_date")
    ]
    candidates.sort(key=lambda album: album.get("first_release_date") or "9999-99-99")
    core_albums = [
        album
        for album in candidates
        if album_has_core_producer(album, releases_by_group, recording_releases)
    ]
    producer_albums = [album for album in candidates if album.get("has_producer")]

    selected = core_albums[:3]
    if not selected:
        selected = producer_albums[:3]
    if not selected:
        raise ValueError(f"no producer album found for {result['name']}")

    for album in candidates:
        if len(selected) >= 2 and len(core_albums) >= 2:
            break
        if album not in selected:
            selected.append(album)
        if len(selected) >= 3:
            break

    return selected[:3]


def load_cache(raw_dir: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    by_url: dict[str, dict[str, Any]] = {}
    for path in sorted(raw_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        url = payload.get("url")
        data = payload.get("data")
        if not url or data is None:
            continue
        entry = {
            "url": url,
            "fetched_at": payload.get("fetched_at"),
            "data": data,
        }
        entries.append(entry)
        by_url[url] = entry
    return entries, by_url


def build_indexes(
    entries: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
]:
    release_groups: dict[str, dict[str, Any]] = {}
    artist_lookups: dict[str, dict[str, Any]] = {}
    recording_releases: dict[str, dict[str, Any]] = {}
    releases_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for entry in entries:
        url = entry["url"]
        data = entry["data"]
        if "/release-group?" in url and "artist=" in url:
            for group in data.get("release-groups", []):
                release_groups.setdefault(
                    group["id"],
                    {"data": group, "fetched_at": entry["fetched_at"]},
                )
        elif "/artist/" in url and "inc=url-rels" in url:
            artist_id = url.split("/artist/", 1)[1].split("?", 1)[0]
            artist_lookups.setdefault(
                artist_id,
                {"data": data, "fetched_at": entry["fetched_at"]},
            )
        elif "/release?" in url and "release-group=" in url:
            group_id = url.split("release-group=", 1)[1].split("&", 1)[0]
            releases_by_group[group_id].extend(data.get("releases", []))
        elif "/release/" in url and "recordings" in url:
            release_id = url.split("/release/", 1)[1].split("?", 1)[0]
            recording_releases.setdefault(
                release_id,
                {"data": data, "fetched_at": entry["fetched_at"]},
            )

    return release_groups, artist_lookups, recording_releases, releases_by_group


def build_fixtures(
    spike_results: dict[str, Any],
    entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
    release_groups, artist_lookups, recording_releases, releases_by_group = build_indexes(
        entries
    )
    results_by_name = {result["name"]: result for result in spike_results["results"]}

    source_records: dict[str, dict[str, Any]] = {}
    artists: dict[str, dict[str, Any]] = {}
    artist_subgenres: list[dict[str, Any]] = []
    external_ids: list[dict[str, Any]] = []
    release_group_records: dict[str, dict[str, Any]] = {}
    release_records: dict[str, dict[str, Any]] = {}
    recording_records: dict[str, dict[str, Any]] = {}
    recording_release_records: dict[str, dict[str, Any]] = {}
    credits: dict[str, dict[str, Any]] = {}
    used_roles: set[str] = set()
    band_summaries: list[dict[str, Any]] = []
    selection_notes: dict[str, str] = {}

    def add_source_record(
        entity_type: str,
        external_id: str,
        source_url: str,
        fetched_at: str | None,
        payload: Any,
    ) -> str:
        source_id = stable_id(
            "source",
            f"{SOURCE}:{entity_type}:{external_id}:{source_url}",
        )
        if source_id not in source_records:
            source_records[source_id] = {
                "id": source_id,
                "source": SOURCE,
                "source_entity_type": entity_type,
                "external_id": external_id,
                "source_url": source_url,
                "fetched_at": fetched_at,
                "license": LICENSE,
                "payload_hash": hash_json(payload),
                "fixture_version": FIXTURE_VERSION,
            }
        return source_id

    def add_artist(
        artist_data: dict[str, Any],
        fetched_at: str | None,
    ) -> str:
        mbid = artist_data["id"]
        artist_id = stable_id("artist", mbid)
        name = artist_data.get("name") or mbid
        source_id = add_source_record(
            "artist",
            mbid,
            f"https://musicbrainz.org/artist/{mbid}",
            fetched_at,
            artist_data,
        )
        if artist_id not in artists:
            artists[artist_id] = {
                "id": artist_id,
                "mbid": mbid,
                "name": name,
                "sort_name": artist_data.get("sort-name") or name,
                "type": str(artist_data.get("type") or "other").casefold(),
                "country": artist_data.get("country"),
                "disambiguation": artist_data.get("disambiguation") or "",
                "source_record_id": source_id,
            }
        return artist_id

    def add_credit(
        relation: dict[str, Any],
        scope: str,
        release_group_id: str,
        release_id: str | None,
        recording_id: str | None,
        source_record_id: str,
        fetched_at: str | None,
    ) -> bool:
        role = map_role(relation)
        if role is None or relation.get("target-type") != "artist":
            return False
        artist_data = relation.get("artist") or {}
        if not artist_data.get("id"):
            return False

        role_code, _, _ = role
        artist_id = add_artist(artist_data, fetched_at)
        target_id = recording_id or release_id or release_group_id
        credit_id = stable_id(
            "credit",
            f"{scope}:{artist_data['id']}:{role_code}:{target_id}",
        )
        if credit_id in credits:
            return True

        used_roles.add(role_code)
        credits[credit_id] = {
            "id": credit_id,
            "artist_id": artist_id,
            "role_code": role_code,
            "scope": scope,
            "release_group_id": release_group_id,
            "release_id": release_id,
            "recording_id": recording_id,
            "source_record_id": source_record_id,
            "confidence": 1.0,
            "status": "confirmed",
            "credited_as": relation.get("target-credit") or None,
            "attributes": {
                "source_type": relation.get("type"),
                "source_attributes": relation.get("attributes", []),
                "source_credit": relation.get("source-credit"),
                "target_credit": relation.get("target-credit"),
            },
        }
        return True

    for band_name, subgenre_name in BANDS:
        result = results_by_name.get(band_name)
        if not result or result.get("status") != "ok":
            raise ValueError(f"missing successful spike result for {band_name}")

        matched = result["matched_artist"]
        artist_mbid = matched["mbid"]
        artist_lookup = artist_lookups.get(artist_mbid)
        artist_data = (
            artist_lookup["data"]
            if artist_lookup
            else {
                "id": artist_mbid,
                "name": matched.get("name") or band_name,
                "sort-name": matched.get("name") or band_name,
                "type": matched.get("type") or "Group",
                "country": matched.get("country"),
                "disambiguation": matched.get("disambiguation") or "",
            }
        )
        artist_fetched_at = (
            artist_lookup["fetched_at"]
            if artist_lookup
            else spike_results.get("generated_at")
        )
        band_id = add_artist(artist_data, artist_fetched_at)
        subgenre_code = SUBGENRES[subgenre_name]
        artist_subgenres.append(
            {
                "artist_id": band_id,
                "subgenre_code": subgenre_code,
                "is_primary": True,
                "confidence": 1.0,
                "source_record_id": artists[band_id]["source_record_id"],
            }
        )

        qid = matched.get("wikidata_qid")
        if qid:
            external_ids.append(
                {
                    "id": stable_id("external", f"artist:{band_id}:wikidata:{qid}"),
                    "entity_type": "artist",
                    "entity_id": band_id,
                    "source": "wikidata",
                    "external_id": qid,
                    "url": f"https://www.wikidata.org/wiki/{qid}",
                }
            )

        albums = choose_albums(result, releases_by_group, recording_releases)
        if len(albums) < 3:
            selection_notes[band_name] = (
                f"Only {len(albums)} eligible studio album(s) in the spike sample."
            )

        band_producer_credits = 0
        for album in albums:
            release_group_id = album["release_group_id"]
            group_entry = release_groups.get(release_group_id)
            if not group_entry:
                raise ValueError(f"missing release-group cache for {release_group_id}")
            group_data = group_entry["data"]
            group_source_id = add_source_record(
                "release_group",
                release_group_id,
                f"https://musicbrainz.org/release-group/{release_group_id}",
                group_entry["fetched_at"],
                group_data,
            )
            release_group_records[release_group_id] = {
                "id": stable_id("release_group", release_group_id),
                "mbid": release_group_id,
                "artist_id": band_id,
                "title": group_data.get("title") or album.get("title"),
                "first_release_date": group_data.get("first-release-date")
                or album.get("first_release_date"),
                "first_release_precision": date_precision(
                    group_data.get("first-release-date")
                    or album.get("first_release_date")
                ),
                "primary_type": str(group_data.get("primary-type") or "album").casefold(),
                "secondary_types": group_data.get("secondary-types") or [],
                "disambiguation": group_data.get("disambiguation") or "",
                "source_record_id": group_source_id,
            }

            releases = releases_by_group.get(release_group_id, [])
            credit_release = choose_credit_release(releases)
            credit_release_id = credit_release["id"]
            credit_release_source_id = add_source_record(
                "release",
                credit_release_id,
                f"https://musicbrainz.org/release/{credit_release_id}",
                next(
                    (
                        entry["fetched_at"]
                        for entry in entries
                        if f"/release?release-group={release_group_id}" in entry["url"]
                    ),
                    None,
                ),
                credit_release,
            )
            release_records[credit_release_id] = {
                "id": stable_id("release", credit_release_id),
                "mbid": credit_release_id,
                "release_group_id": stable_id("release_group", release_group_id),
                "title": credit_release.get("title") or album.get("title"),
                "release_date": credit_release.get("date"),
                "release_date_precision": date_precision(credit_release.get("date")),
                "country": credit_release.get("country"),
                "status": credit_release.get("status"),
                "source_record_id": credit_release_source_id,
            }

            for relation in credit_release.get("relations", []):
                if add_credit(
                    relation,
                    "release",
                    stable_id("release_group", release_group_id),
                    stable_id("release", credit_release_id),
                    None,
                    credit_release_source_id,
                    next(
                        (
                            entry["fetched_at"]
                            for entry in entries
                            if f"/release?release-group={release_group_id}" in entry["url"]
                        ),
                        None,
                    ),
                ):
                    role = map_role(relation)
                    if role and role[0] in {"producer", "co-producer"}:
                        band_producer_credits += 1

            recording_release_id = album.get("recording_credit_release_id")
            if recording_release_id:
                recording_entry = recording_releases.get(recording_release_id)
                if recording_entry:
                    recording_data = recording_entry["data"]
                    recording_source_id = add_source_record(
                        "release",
                        recording_release_id,
                        f"https://musicbrainz.org/release/{recording_release_id}",
                        recording_entry["fetched_at"],
                        recording_data,
                    )
                    if recording_release_id not in release_records:
                        release_records[recording_release_id] = {
                            "id": stable_id("release", recording_release_id),
                            "mbid": recording_release_id,
                            "release_group_id": stable_id(
                                "release_group", release_group_id
                            ),
                            "title": recording_data.get("title") or album.get("title"),
                            "release_date": recording_data.get("date"),
                            "release_date_precision": date_precision(
                                recording_data.get("date")
                            ),
                            "country": recording_data.get("country"),
                            "status": recording_data.get("status"),
                            "source_record_id": recording_source_id,
                        }

                    for medium in recording_data.get("media", []):
                        for track in medium.get("tracks", []):
                            recording = track.get("recording") or {}
                            recording_mbid = recording.get("id")
                            if not recording_mbid:
                                continue
                            recording_source = add_source_record(
                                "recording",
                                recording_mbid,
                                f"https://musicbrainz.org/recording/{recording_mbid}",
                                recording_entry["fetched_at"],
                                recording,
                            )
                            recording_records[recording_mbid] = {
                                "id": stable_id("recording", recording_mbid),
                                "mbid": recording_mbid,
                                "title": recording.get("title") or "",
                                "source_record_id": recording_source,
                            }
                            link_id = stable_id(
                                "recording_release",
                                f"{recording_release_id}:{recording_mbid}",
                            )
                            recording_release_records[link_id] = {
                                "id": link_id,
                                "release_id": stable_id("release", recording_release_id),
                                "recording_id": stable_id("recording", recording_mbid),
                                "disc": str(medium.get("position") or "") or None,
                                "position": str(
                                    track.get("position") or track.get("number") or ""
                                )
                                or None,
                            }
                            for relation in recording.get("relations", []):
                                if add_credit(
                                    relation,
                                    "recording",
                                    stable_id("release_group", release_group_id),
                                    stable_id("release", recording_release_id),
                                    stable_id("recording", recording_mbid),
                                    recording_source,
                                    recording_entry["fetched_at"],
                                ):
                                    role = map_role(relation)
                                    if role and role[0] in {"producer", "co-producer"}:
                                        band_producer_credits += 1

        if band_producer_credits == 0:
            raise ValueError(f"no producer/co-producer credits extracted for {band_name}")
        band_summaries.append(
            {
                "name": band_name,
                "subgenre": subgenre_name,
                "album_count": len(albums),
                "producer_credit_count": band_producer_credits,
            }
        )

    roles = [
        {
            "code": code,
            "name": name,
            "category": category,
        }
        for code, (name, category) in sorted(ROLE_DEFINITIONS.items())
        if code in used_roles
    ]

    return {
        "source_records": sorted(source_records.values(), key=lambda row: row["id"]),
        "artists": sorted(artists.values(), key=lambda row: (row["name"], row["id"])),
        "subgenres": [
            {"code": code, "name": name}
            for name, code in sorted(SUBGENRES.items(), key=lambda item: item[1])
        ],
        "artist_subgenres": sorted(
            artist_subgenres,
            key=lambda row: (row["subgenre_code"], row["artist_id"]),
        ),
        "external_ids": sorted(external_ids, key=lambda row: row["id"]),
        "release_groups": sorted(
            release_group_records.values(),
            key=lambda row: (row["first_release_date"] or "", row["id"]),
        ),
        "releases": sorted(release_records.values(), key=lambda row: row["id"]),
        "recordings": sorted(recording_records.values(), key=lambda row: row["id"]),
        "recording_releases": sorted(
            recording_release_records.values(),
            key=lambda row: row["id"],
        ),
        "roles": roles,
        "credits": sorted(credits.values(), key=lambda row: row["id"]),
        "manifest": {
            "version": FIXTURE_VERSION,
            "generated_at": "2026-11-06",
            "source": SOURCE,
            "source_snapshot": spike_results.get("generated_at"),
            "license": LICENSE,
            "builder": "scripts/build_e2_fixtures.py",
            "selection_policy": (
                "Prefer albums with core producer/co-producer credits, using the "
                "earliest official release for release-level provenance."
            ),
            "band_count": len(band_summaries),
            "subgenre_distribution": dict(
                Counter(band["subgenre"] for band in band_summaries)
            ),
            "source_record_count": len(source_records),
            "artist_count": len(artists),
            "release_group_count": len(release_group_records),
            "release_count": len(release_records),
            "recording_count": len(recording_records),
            "recording_release_count": len(recording_release_records),
            "role_count": len(roles),
            "subgenre_count": len(SUBGENRES),
            "artist_subgenre_count": len(artist_subgenres),
            "external_id_count": len(external_ids),
            "album_count": len(release_group_records),
            "credit_count": len(credits),
            "credit_scope_distribution": dict(
                Counter(credit["scope"] for credit in credits.values())
            ),
            "role_distribution": dict(
                Counter(credit["role_code"] for credit in credits.values())
            ),
            "bands": band_summaries,
            "selection_notes": selection_notes,
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("spike/output/raw"))
    parser.add_argument(
        "--spike-results",
        type=Path,
        default=Path("spike/output/spike_results.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/fixtures/e2"),
    )
    args = parser.parse_args()

    if not args.raw_dir.is_dir():
        raise SystemExit(f"raw cache directory not found: {args.raw_dir}")
    if not args.spike_results.is_file():
        raise SystemExit(f"spike results not found: {args.spike_results}")

    spike_results = json.loads(args.spike_results.read_text(encoding="utf-8"))
    entries, _ = load_cache(args.raw_dir)
    fixtures = build_fixtures(spike_results, entries)

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = fixtures.pop("manifest")
    file_checksums: dict[str, str] = {}

    for name, value in fixtures.items():
        path = args.output / f"{name}.json"
        write_json(path, value)
        file_checksums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()

    manifest["files"] = dict(sorted(file_checksums.items()))
    write_json(args.output / "manifest.json", manifest)
    print(f"Wrote {args.output} with {manifest['band_count']} bands")
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
