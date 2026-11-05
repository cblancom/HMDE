#!/usr/bin/env python3
"""MusicBrainz feasibility spike for HMDE.

This is a disposable research script. It is not part of the product and will
not be imported by the API or the production ETL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "HMDE-Spike/0.1 (https://example.org/hmde; hmde-spike@example.org)"
MIN_INTERVAL_SECONDS = 1.1
MAX_RETRIES = 5
MAX_RELEASE_GROUPS_PER_ARTIST = 400
MAX_RELEASES_PER_ALBUM = 200

ROOT = Path(__file__).resolve().parent
SAMPLE_PATH = ROOT / "sample.json"
OUTPUT_DIR = ROOT / "output"
RAW_DIR = OUTPUT_DIR / "raw"
RESULTS_PATH = OUTPUT_DIR / "spike_results.json"
PARTIAL_PATH = OUTPUT_DIR / "spike_results_partial.json"
REPORT_PATH = OUTPUT_DIR / "spike_report.md"
COLLECTION_METADATA_PATH = OUTPUT_DIR / "collection_metadata.json"

CORE_ROLES = {"producer", "co-producer"}
EXTENDED_ROLES = {"executive producer", "engineer", "mix", "mastering"}
STUDIO_RELATION_TYPES = {
    "recorded at",
    "mixed at",
    "mastered at",
    "recorded in",
    "mixed in",
    "mastered in",
}
SUSPICIOUS_TITLE_PATTERN = re.compile(
    r"\b(demo|demos|split|live|compilation|best of|greatest|anthology|collection|single|ep)\b"
    r"|(?:vol\.|vs\.)",
    re.IGNORECASE,
)


class MusicBrainzClient:
    def __init__(self, use_cache: bool = True) -> None:
        self.use_cache = use_cache
        self.last_network_request = 0.0
        self.network_requests = 0
        self.cache_hits = 0
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return RAW_DIR / f"{digest}.json"

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self.last_network_request
        remaining = MIN_INTERVAL_SECONDS - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def get(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        query = urllib.parse.urlencode(params)
        url = f"{BASE_URL}{path}?{query}"
        cache_path = self._cache_path(url)

        if self.use_cache and cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            self.cache_hits += 1
            return payload["data"]

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            self._wait_for_rate_limit()
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=40) as response:
                    data = json.loads(response.read().decode("utf-8"))
                self.last_network_request = time.monotonic()
                self.network_requests += 1
                cache_path.write_text(
                    json.dumps(
                        {
                            "url": url,
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                            "data": data,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return data
            except urllib.error.HTTPError as exc:
                self.last_network_request = time.monotonic()
                self.network_requests += 1
                if exc.code == 404:
                    return None
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(min(delay, 60))
            except (urllib.error.URLError, TimeoutError) as exc:
                self.last_network_request = time.monotonic()
                self.network_requests += 1
                last_error = exc
                time.sleep(min(2**attempt, 60))

        raise RuntimeError(f"MusicBrainz request failed after retries: {url}") from last_error


def year_from_date(value: str | None) -> int | None:
    if not value or len(value) < 4 or not value[:4].isdigit():
        return None
    return int(value[:4])


def date_precision(value: str | None) -> str:
    if not value:
        return "unknown"
    if len(value) >= 10 and value[4:5] == "-" and value[7:8] == "-":
        return "day"
    if len(value) == 7 and value[4:5] == "-":
        return "month"
    if len(value) == 4 and value.isdigit():
        return "year"
    return "unknown"


def in_period(value: str | None) -> bool:
    year = year_from_date(value)
    return year is not None and 1980 <= year <= 2000


def low_confidence_reason(title: str | None, release_count: int) -> str | None:
    reasons: list[str] = []
    if release_count <= 2:
        reasons.append("two or fewer releases")
    if title and SUSPICIOUS_TITLE_PATTERN.search(title):
        reasons.append("title suggests non-studio release")
    return "; ".join(reasons) if reasons else None


def choose_artist(candidates: list[dict[str, Any]], wanted_name: str) -> dict[str, Any] | None:
    def rank(artist: dict[str, Any]) -> tuple[int, int, int]:
        exact = int(artist.get("name", "").casefold() == wanted_name.casefold())
        group = int(artist.get("type") == "Group")
        return exact, group, int(artist.get("score", 0))

    if not candidates:
        return None
    return max(candidates, key=rank)


def search_artist(client: MusicBrainzClient, name: str) -> dict[str, Any] | None:
    data = client.get(
        "/artist",
        {
            "query": f'artist:"{name}"',
            "limit": 10,
            "fmt": "json",
        },
    )
    if not data:
        return None
    return choose_artist(data.get("artists", []), name)


def fetch_wikidata_qid(client: MusicBrainzClient, mbid: str) -> str | None:
    data = client.get(f"/artist/{mbid}", {"inc": "url-rels", "fmt": "json"})
    if not data:
        return None
    for relation in data.get("relations", []):
        url = (relation.get("url") or {}).get("resource", "")
        if relation.get("type") == "wikidata" or "wikidata.org/wiki/Q" in url:
            return url.rsplit("/", 1)[-1]
    return None


def fetch_release_groups(client: MusicBrainzClient, mbid: str) -> tuple[list[dict[str, Any]], int]:
    groups: list[dict[str, Any]] = []
    offset = 0
    total = 0
    while True:
        data = client.get(
            "/release-group",
            {
                "artist": mbid,
                "type": "album",
                "limit": 100,
                "offset": offset,
                "inc": "artist-rels+place-rels+genres+tags",
                "fmt": "json",
            },
        )
        if not data:
            break
        page = data.get("release-groups", [])
        total = int(data.get("release-group-count", total))
        groups.extend(page)
        offset += len(page)
        if not page or offset >= total or offset >= MAX_RELEASE_GROUPS_PER_ARTIST:
            break
    return groups, total


def fetch_releases(client: MusicBrainzClient, release_group_id: str) -> tuple[list[dict[str, Any]], int]:
    releases: list[dict[str, Any]] = []
    offset = 0
    total = 0
    while True:
        data = client.get(
            "/release",
            {
                "release-group": release_group_id,
                "limit": 100,
                "offset": offset,
                "inc": "artist-rels+place-rels",
                "fmt": "json",
            },
        )
        if not data:
            break
        page = data.get("releases", [])
        total = int(data.get("release-count", total))
        releases.extend(page)
        offset += len(page)
        if not page or offset >= total or offset >= MAX_RELEASES_PER_ALBUM:
            break
    return releases, total


def extract_relations(
    releases: list[dict[str, Any]],
    group_relations: list[dict[str, Any]],
    recording_relations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    role_artists: dict[str, set[str]] = {}
    studio_names: set[str] = set()
    studio_relation_count = 0

    def consume(relations: list[dict[str, Any]]) -> None:
        nonlocal studio_relation_count
        for relation in relations:
            target_type = relation.get("target-type")
            relation_type = str(relation.get("type", "")).casefold()
            if target_type == "artist":
                artist = relation.get("artist") or {}
                name = artist.get("name") or artist.get("id") or ""
                attributes = {
                    str(attribute).casefold()
                    for attribute in relation.get("attributes", [])
                }
                if relation_type == "producer":
                    if "co" in attributes:
                        relation_type = "co-producer"
                    elif "executive" in attributes:
                        relation_type = "executive producer"
                    elif "assistant" in attributes:
                        relation_type = "assistant producer"
                    elif "additional" in attributes:
                        relation_type = "additional producer"
                if name:
                    role_artists.setdefault(relation_type, set()).add(name)
            elif target_type == "place":
                studio_relation_count += 1
                place = relation.get("place") or {}
                if place.get("name"):
                    studio_names.add(place["name"])
            elif relation_type in STUDIO_RELATION_TYPES:
                studio_relation_count += 1

    consume(group_relations)
    for release in releases:
        consume(release.get("relations", []))
    consume(recording_relations or [])

    role_counts = {role: len(names) for role, names in role_artists.items()}
    producer_names = role_artists.get("producer", set()) | role_artists.get("co-producer", set())
    engineer_names = (
        role_artists.get("engineer", set())
        | role_artists.get("mix", set())
        | role_artists.get("mastering", set())
    )
    return {
        "role_types": dict(sorted(role_counts.items())),
        "producer_names": sorted(producer_names),
        "engineer_names": sorted(engineer_names),
        "studio_names": sorted(studio_names),
        "studio_relation_count": studio_relation_count,
        "has_producer": bool(role_counts.get("producer") or role_counts.get("co-producer")),
        "has_co_producer": bool(role_counts.get("co-producer")),
        "has_executive_producer": bool(role_counts.get("executive producer")),
        "has_engineer": bool(role_counts.get("engineer")),
        "has_mix": bool(role_counts.get("mix")),
        "has_mastering": bool(role_counts.get("mastering")),
        "has_studio": studio_relation_count > 0,
    }


def fetch_recording_relations(
    client: MusicBrainzClient, release_id: str
) -> list[dict[str, Any]]:
    data = client.get(
        f"/release/{release_id}",
        {
            "inc": "recordings+recording-level-rels+artist-rels+place-rels",
            "fmt": "json",
        },
    )
    if not data:
        return []
    relations: list[dict[str, Any]] = list(data.get("relations", []))
    for medium in data.get("media", []):
        for track in medium.get("tracks", []):
            recording = track.get("recording") or {}
            relations.extend(recording.get("relations", []))
    return relations


def choose_representative_release(releases: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not releases:
        return None
    official = [release for release in releases if release.get("status") == "Official"]
    pool = official or releases
    dated = [release for release in pool if release.get("date")]
    return min(dated or pool, key=lambda release: release.get("date") or "9999")


def analyze_band(
    client: MusicBrainzClient,
    entry: dict[str, Any],
) -> dict[str, Any]:
    name = entry["name"]
    print(f"\n[{entry['subgenre']}] {name}: searching artist...", flush=True)
    artist = search_artist(client, name)
    if not artist:
        return {
            **entry,
            "status": "artist_not_found",
            "albums": [],
        }

    mbid = artist["id"]
    qid = fetch_wikidata_qid(client, mbid)
    groups, group_total = fetch_release_groups(client, mbid)
    studio_albums = [
        group
        for group in groups
        if group.get("primary-type", "").casefold() == "album"
        and not group.get("secondary-types")
        and in_period(group.get("first-release-date"))
    ]
    studio_albums.sort(key=lambda group: group.get("first-release-date") or "")

    print(
        f"  artist={artist.get('name')} mbid={mbid} qid={qid} "
        f"release_groups={group_total} studio_albums={len(studio_albums)}",
        flush=True,
    )

    albums: list[dict[str, Any]] = []
    for index, group in enumerate(studio_albums, start=1):
        releases, release_total = fetch_releases(client, group["id"])
        release_relation_data = extract_relations(releases, group.get("relations", []))
        relation_data = release_relation_data
        recording_credit_checked = False
        recording_credit_release_id = None
        if not relation_data["has_producer"] and releases:
            representative = choose_representative_release(releases)
            if representative:
                recording_credit_release_id = representative["id"]
                recording_relations = fetch_recording_relations(client, representative["id"])
                relation_data = extract_relations(
                    releases,
                    group.get("relations", []),
                    recording_relations,
                )
                recording_credit_checked = True
        genres = [genre["name"] for genre in group.get("genres", [])][:5]
        suspicion = low_confidence_reason(group.get("title"), release_total)
        album = {
            "release_group_id": group["id"],
            "title": group.get("title"),
            "first_release_date": group.get("first-release-date"),
            "date_precision": date_precision(group.get("first-release-date")),
            "genres": genres,
            "release_count": release_total,
            "releases_fetched": len(releases),
            "releases_truncated": release_total > len(releases),
            "recording_credit_checked": recording_credit_checked,
            "recording_credit_release_id": recording_credit_release_id,
            "release_level_has_producer": release_relation_data["has_producer"],
            "producer_only_at_recording": (
                not release_relation_data["has_producer"]
                and relation_data["has_producer"]
            ),
            "low_confidence": bool(suspicion),
            "low_confidence_reason": suspicion,
            **relation_data,
        }
        albums.append(album)
        print(
            f"  [{index}/{len(studio_albums)}] {album['title']} "
            f"({album['first_release_date']}): producer={album['has_producer']} "
            f"engineer={album['has_engineer'] or album['has_mix'] or album['has_mastering']} "
            f"studio={album['has_studio']} releases={len(releases)}/{release_total} "
            f"recording_check={recording_credit_checked}",
            flush=True,
        )

    return {
        **entry,
        "status": "ok",
        "matched_artist": {
            "mbid": mbid,
            "name": artist.get("name"),
            "type": artist.get("type"),
            "country": artist.get("country"),
            "disambiguation": artist.get("disambiguation"),
            "score": artist.get("score"),
            "wikidata_qid": qid,
        },
        "release_group_count": group_total,
        "studio_album_count": len(studio_albums),
        "albums": albums,
    }


def percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator / denominator:.1f}%"


def build_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    albums = [
        album
        for band in results
        if band.get("status") == "ok"
        for album in band.get("albums", [])
    ]
    all_role_types: Counter[str] = Counter()
    producers: set[str] = set()
    studios: set[str] = set()
    for album in albums:
        all_role_types.update(album.get("role_types", {}))
        producers.update(album.get("producer_names", []))
        studios.update(album.get("studio_names", []))

    total = len(albums)
    date_precisions = Counter(album["date_precision"] for album in albums)
    truncated = sum(1 for album in albums if album["releases_truncated"])
    with_producer = sum(1 for album in albums if album["has_producer"])
    with_co_producer = sum(1 for album in albums if album["has_co_producer"])
    with_executive = sum(1 for album in albums if album["has_executive_producer"])
    with_engineer = sum(1 for album in albums if album["has_engineer"])
    with_mix = sum(1 for album in albums if album["has_mix"])
    with_mastering = sum(1 for album in albums if album["has_mastering"])
    with_extended = sum(
        1
        for album in albums
        if album["has_executive_producer"]
        or album["has_engineer"]
        or album["has_mix"]
        or album["has_mastering"]
    )
    with_studio = sum(1 for album in albums if album["has_studio"])
    low_confidence = sum(1 for album in albums if album.get("low_confidence"))
    clean_albums = [album for album in albums if not album.get("low_confidence")]
    clean_total = len(clean_albums)
    clean_with_producer = sum(1 for album in clean_albums if album["has_producer"])
    with_qid = sum(
        1
        for band in results
        if band.get("status") == "ok" and band.get("matched_artist", {}).get("wikidata_qid")
    )
    bands_ok = sum(1 for band in results if band.get("status") == "ok")

    return {
        "bands_total": len(results),
        "bands_ok": bands_ok,
        "bands_not_found": len(results) - bands_ok,
        "albums_total": total,
        "albums_with_producer": with_producer,
        "albums_with_co_producer": with_co_producer,
        "albums_with_executive_producer": with_executive,
        "albums_with_engineer": with_engineer,
        "albums_with_mix": with_mix,
        "albums_with_mastering": with_mastering,
        "albums_with_extended_credit": with_extended,
        "albums_with_studio": with_studio,
        "albums_with_truncated_releases": truncated,
        "albums_with_recording_credit_check": sum(
            1 for album in albums if album.get("recording_credit_checked")
        ),
        "albums_producer_only_at_recording": sum(
            1 for album in albums if album.get("producer_only_at_recording")
        ),
        "albums_low_confidence": low_confidence,
        "albums_clean_total": clean_total,
        "albums_clean_with_producer": clean_with_producer,
        "bands_with_wikidata_qid": with_qid,
        "distinct_producers": len(producers),
        "distinct_studios": len(studios),
        "date_precisions": dict(sorted(date_precisions.items())),
        "role_type_frequencies": dict(all_role_types.most_common()),
        "coverage": {
            "producer_or_co_producer": percentage(with_producer, total),
            "producer_or_co_producer_excluding_low_confidence": percentage(
                clean_with_producer, clean_total
            ),
            "co_producer": percentage(with_co_producer, total),
            "executive_producer": percentage(with_executive, total),
            "engineer": percentage(with_engineer, total),
            "mix": percentage(with_mix, total),
            "mastering": percentage(with_mastering, total),
            "extended_credit": percentage(with_extended, total),
            "studio": percentage(with_studio, total),
            "wikidata_qid_bands": percentage(with_qid, len(results)),
            "date_precision_year_or_better": percentage(
                total - date_precisions.get("unknown", 0), total
            ),
        },
    }


def build_report(
    results: list[dict[str, Any]],
    metrics: dict[str, Any],
    client: MusicBrainzClient,
    elapsed_seconds: float,
) -> str:
    lines: list[str] = []
    lines.append("# MusicBrainz feasibility spike")
    lines.append("")
    lines.append(f"- **Date:** {datetime.now(timezone.utc).date().isoformat()}")
    lines.append(f"- **Sample size:** {metrics['bands_total']} bands")
    if COLLECTION_METADATA_PATH.exists():
        collection = json.loads(COLLECTION_METADATA_PATH.read_text(encoding="utf-8"))
        lines.append(
            f"- **Initial full fetch:** {collection['network_requests']} network requests, "
            f"{collection['elapsed_seconds']:.1f} seconds ({collection['date']})"
        )
    lines.append(
        f"- **This analysis run:** {client.network_requests} network requests, "
        f"{client.cache_hits} cache hits, {elapsed_seconds:.1f} seconds"
    )
    lines.append("")
    lines.append("## Coverage summary")
    lines.append("")
    lines.append("| Metric | Count | Coverage |")
    lines.append("|---|---:|---:|")
    coverage = metrics["coverage"]
    lines.append(
        f"| Albums in period | {metrics['albums_total']} | — |"
    )
    lines.append(
        f"| Albums with producer/co-producer | {metrics['albums_with_producer']} | {coverage['producer_or_co_producer']} |"
    )
    lines.append(
        f"| Producer/co-producer, excluding low-confidence albums "
        f"| {metrics['albums_clean_with_producer']} | "
        f"{coverage['producer_or_co_producer_excluding_low_confidence']} |"
    )
    lines.append(
        f"| Albums with co-producer | {metrics['albums_with_co_producer']} | {coverage['co_producer']} |"
    )
    lines.append(
        f"| Albums with executive producer | {metrics['albums_with_executive_producer']} | {coverage['executive_producer']} |"
    )
    lines.append(
        f"| Albums with engineer | {metrics['albums_with_engineer']} | {coverage['engineer']} |"
    )
    lines.append(
        f"| Albums with mix | {metrics['albums_with_mix']} | {coverage['mix']} |"
    )
    lines.append(
        f"| Albums with mastering | {metrics['albums_with_mastering']} | {coverage['mastering']} |"
    )
    lines.append(
        f"| Albums with any extended credit | {metrics['albums_with_extended_credit']} | {coverage['extended_credit']} |"
    )
    lines.append(
        f"| Albums with studio/place | {metrics['albums_with_studio']} | {coverage['studio']} |"
    )
    lines.append(
        f"| Bands with Wikidata QID | {metrics['bands_with_wikidata_qid']} | {coverage['wikidata_qid_bands']} |"
    )
    lines.append("")
    lines.append("## Per-band results")
    lines.append("")
    lines.append(
        "| Band | Subgenre | Albums | Producer/co-producer | Extended credit | Studio | QID |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for band in results:
        if band.get("status") != "ok":
            lines.append(
                f"| {band['name']} | {band['subgenre']} | — | — | — | — | not found |"
            )
            continue
        albums = band.get("albums", [])
        album_count = len(albums)
        producer_count = sum(1 for album in albums if album["has_producer"])
        extended_count = sum(
            1
            for album in albums
            if album["has_executive_producer"]
            or album["has_engineer"]
            or album["has_mix"]
            or album["has_mastering"]
        )
        studio_count = sum(1 for album in albums if album["has_studio"])
        qid = band["matched_artist"].get("wikidata_qid") or "—"
        lines.append(
            f"| {band['name']} | {band['subgenre']} | {album_count} | "
            f"{producer_count} | {extended_count} | {studio_count} | {qid} |"
        )
    lines.append("")
    lines.append("## Low-confidence release-groups")
    lines.append("")
    lines.append(
        "These release-groups are typed as albums in MusicBrainz but have two or fewer "
        "releases and/or a title suggesting a demo, single, live, split or compilation. "
        "They are included in the main metrics but should be reviewed before ingestion."
    )
    lines.append("")
    lines.append("| Band | Album | Date | Releases | Reason |")
    lines.append("|---|---|---|---:|---|")
    low_confidence_rows = 0
    for band in results:
        if band.get("status") != "ok":
            continue
        for album in band.get("albums", []):
            if album.get("low_confidence"):
                low_confidence_rows += 1
                lines.append(
                    f"| {band['name']} | {album.get('title')} | "
                    f"{album.get('first_release_date') or '—'} | {album.get('release_count')} | "
                    f"{album.get('low_confidence_reason')} |"
                )
    if low_confidence_rows == 0:
        lines.append("| — | — | — | — | none |")
    lines.append("")
    lines.append("## Relation type frequencies")
    lines.append("")
    lines.append("| Relation type | Count |")
    lines.append("|---|---:|")
    for role, count in metrics["role_type_frequencies"].items():
        lines.append(f"| {role} | {count} |")
    lines.append("")
    lines.append("## Data quality observations")
    lines.append("")
    lines.append(f"- Albums with truncated release sampling: {metrics['albums_with_truncated_releases']}")
    lines.append(
        f"- Albums that needed recording-level credit inspection: "
        f"{metrics['albums_with_recording_credit_check']}"
    )
    lines.append(
        f"- Albums whose producer credit exists only at recording level: "
        f"{metrics['albums_producer_only_at_recording']}"
    )
    lines.append(
        f"- Low-confidence albums (two or fewer releases and/or suspicious title): "
        f"{metrics['albums_low_confidence']}"
    )
    lines.append(f"- Distinct producers found: {metrics['distinct_producers']}")
    lines.append(f"- Distinct studios found: {metrics['distinct_studios']}")
    lines.append(f"- Date precision distribution: {metrics['date_precisions']}")
    lines.append(f"- Bands not found: {metrics['bands_not_found']}")
    lines.append("")
    lines.append("## Preliminary interpretation")
    lines.append("")
    producer_coverage = (
        100 * metrics["albums_with_producer"] / metrics["albums_total"]
        if metrics["albums_total"]
        else 0
    )
    if producer_coverage >= 60:
        decision = "MusicBrainz looks viable as the primary source for the MVP."
    elif producer_coverage >= 30:
        decision = (
            "MusicBrainz is viable with limitations; consider Wikipedia as a complement "
            "or adjust the scope before building the full pipeline."
        )
    else:
        decision = (
            "MusicBrainz coverage is below the provisional threshold; do not build the MVP "
            "on this coverage without rethinking sources or scope."
        )
    lines.append(decision)
    lines.append("")
    lines.append(
        "Recording-level credits are inspected only for the earliest official release "
        "when no release-level producer is found; later editions may add credits. "
        "Coverage is therefore conservative."
    )
    lines.append("")
    lines.append(
        "MusicBrainz stores co-producer and executive producer as attributes on the "
        "producer relationship (`co`, `executive`), not as separate relationship types; "
        "the spike maps those attributes explicitly."
    )
    lines.append("")
    lines.append(
        "These thresholds are working hypotheses from `docs/03-data/sources.md`; "
        "the sample is stratified but not statistically representative of the entire scene."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--band", help="Run only one band from the sample")
    parser.add_argument("--max-bands", type=int, help="Limit the number of bands")
    parser.add_argument("--no-cache", action="store_true", help="Disable raw response cache")
    args = parser.parse_args()

    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    if args.band:
        sample = [entry for entry in sample if entry["name"].casefold() == args.band.casefold()]
        if not sample:
            raise SystemExit(f"Band not found in sample: {args.band}")
    if args.max_bands:
        sample = sample[: args.max_bands]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = MusicBrainzClient(use_cache=not args.no_cache)
    started = time.monotonic()
    results: list[dict[str, Any]] = []

    for entry in sample:
        result = analyze_band(client, entry)
        results.append(result)
        PARTIAL_PATH.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    elapsed = time.monotonic() - started
    metrics = build_metrics(results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_agent": USER_AGENT,
        "sample_size": len(results),
        "network_requests": client.network_requests,
        "cache_hits": client.cache_hits,
        "elapsed_seconds": round(elapsed, 1),
        "metrics": metrics,
        "results": results,
    }
    RESULTS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(
        build_report(results, metrics, client, elapsed),
        encoding="utf-8",
    )
    print(f"\nWrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(json.dumps(metrics["coverage"], indent=2))


if __name__ == "__main__":
    main()
