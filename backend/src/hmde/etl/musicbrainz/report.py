"""Coverage and failure reports for MusicBrainz ingestion."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from hmde.etl.musicbrainz.traversal import BandExtraction

COVERAGE_FILE = "coverage.json"
REPORT_FILE = "report.md"
INTERPRETATION = (
    "Missing data is not negative evidence: absence of a credit, date, identifier "
    "or studio relationship means that the source did not provide it in this snapshot."
)
PRODUCER_ROLES = {"producer", "co-producer"}


@dataclass(frozen=True, slots=True)
class ReportResult:
    coverage_path: Path
    report_path: Path
    coverage: dict[str, Any]


def build_coverage(
    extractions: Iterable[BandExtraction],
    *,
    dataset_version: str | None = None,
    seed_list_version: str | None = None,
    source_snapshot_at: datetime | None = None,
    code_version: str | None = None,
    counters: Mapping[str, Any] | None = None,
    failures: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    extraction_list = list(extractions)
    roles: Counter[str] = Counter()
    scopes: Counter[str] = Counter()
    exclusions_by_reason: Counter[str] = Counter()
    bands: list[dict[str, Any]] = []
    subgenres: defaultdict[str, dict[str, Any]] = defaultdict(_new_group_stats)
    decades: defaultdict[str, dict[str, Any]] = defaultdict(_new_group_stats)

    for extraction in extraction_list:
        producer_groups = _producer_groups(extraction)
        release_count_by_group = Counter(
            release.release_group_mbid for release in extraction.releases
        )
        band_roles = Counter(credit.role for credit in extraction.credits)
        band_scopes = Counter(credit.scope for credit in extraction.credits)
        roles.update(band_roles)
        scopes.update(band_scopes)

        exclusion_counts = Counter(exclusion.reason for exclusion in extraction.exclusions)
        exclusions_by_reason.update(exclusion_counts)

        albums_with_producer = sum(
            1 for group in extraction.release_groups if group.mbid in producer_groups
        )
        qid_present = any(
            item.entity_type == "artist" and item.source == "wikidata"
            for item in extraction.external_ids
        )

        bands.append(
            {
                "mbid": extraction.band_mbid,
                "name": extraction.artist.name,
                "subgenre": extraction.subgenre,
                "has_wikidata_qid": qid_present,
                "release_groups": len(extraction.release_groups),
                "releases": len(extraction.releases),
                "recordings": len(extraction.recordings),
                "credits": len(extraction.credits),
                "credits_by_role": dict(sorted(band_roles.items())),
                "credits_by_scope": dict(sorted(band_scopes.items())),
                "places": len(extraction.places),
                "exclusions": len(extraction.exclusions),
                "exclusions_by_reason": dict(sorted(exclusion_counts.items())),
                "albums_with_producer": albums_with_producer,
            }
        )

        subgenre_stats = subgenres[extraction.subgenre]
        _add_band_stats(
            subgenre_stats,
            extraction,
            albums_with_producer=albums_with_producer,
            producer_groups=producer_groups,
            qid_present=qid_present,
            exclusion_count=len(extraction.exclusions),
        )

        for group in extraction.release_groups:
            decade = _decade(group.first_release_date)
            decade_stats = decades[decade]
            _add_band_stats(
                decade_stats,
                extraction,
                albums_with_producer=albums_with_producer,
                producer_groups=producer_groups,
                qid_present=qid_present,
                exclusion_count=0,
                release_group=group.mbid,
                release_count=release_count_by_group[group.mbid],
            )

    band_count = len(extraction_list)
    summary = {
        "bands": band_count,
        "bands_with_wikidata_qid": sum(1 for band in bands if band["has_wikidata_qid"]),
        "bands_with_producer": sum(1 for band in bands if band["albums_with_producer"] > 0),
        "release_groups": sum(band["release_groups"] for band in bands),
        "albums_with_producer": sum(band["albums_with_producer"] for band in bands),
        "releases": sum(band["releases"] for band in bands),
        "recordings": sum(band["recordings"] for band in bands),
        "credits": sum(band["credits"] for band in bands),
        "places": sum(band["places"] for band in bands),
        "exclusions": sum(band["exclusions"] for band in bands),
    }

    failures_list = [_jsonable(dict(failure)) for failure in failures]
    failures_list.sort(
        key=lambda failure: (
            str(failure.get("band_mbid") or ""),
            str(failure.get("phase") or ""),
            str(failure.get("error_type") or ""),
            str(failure.get("message") or ""),
        )
    )

    for stats in subgenres.values():
        stats["bands"] = len(stats["_band_ids"])
        stats["bands_with_producer"] = len(stats["_bands_with_producer"])
        stats["bands_with_wikidata_qid"] = len(stats["_bands_with_qid"])
        _drop_internal_sets(stats)
    for stats in decades.values():
        stats["bands"] = len(stats["_band_ids"])
        stats["bands_with_producer"] = len(stats["_bands_with_producer"])
        stats["bands_with_wikidata_qid"] = len(stats["_bands_with_qid"])
        _drop_internal_sets(stats)

    return {
        "dataset": {
            "dataset_version": dataset_version,
            "seed_list_version": seed_list_version,
            "source_snapshot_at": _datetime_string(source_snapshot_at),
            "code_version": code_version,
        },
        "summary": summary,
        "credits_by_role": dict(sorted(roles.items())),
        "credits_by_scope": dict(sorted(scopes.items())),
        "exclusions_by_reason": dict(sorted(exclusions_by_reason.items())),
        "subgenres": {name: _sorted_stats(stats) for name, stats in sorted(subgenres.items())},
        "decades": {
            name: _sorted_stats(stats)
            for name, stats in sorted(decades.items(), key=lambda item: _decade_order(item[0]))
        },
        "bands": sorted(bands, key=lambda band: (str(band["name"]).casefold(), band["mbid"])),
        "run": {
            "counters": _jsonable(dict(counters or {})),
            "failures": failures_list,
        },
        "interpretation": INTERPRETATION,
    }


def render_report(coverage: Mapping[str, Any]) -> str:
    dataset = coverage["dataset"]
    summary = coverage["summary"]
    lines: list[str] = [
        "# MusicBrainz ingestion coverage",
        "",
        f"- Dataset version: {dataset['dataset_version'] or 'unknown'}",
        f"- Seed list version: {dataset['seed_list_version'] or 'unknown'}",
        f"- Source snapshot: {dataset['source_snapshot_at'] or 'unknown'}",
        f"- Code version: {dataset['code_version'] or 'unknown'}",
        "",
        f"> {coverage['interpretation']}",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for label, key in (
        ("Bands", "bands"),
        ("Bands with Wikidata QID", "bands_with_wikidata_qid"),
        ("Bands with producer/co-producer", "bands_with_producer"),
        ("Release groups", "release_groups"),
        ("Release groups with producer/co-producer", "albums_with_producer"),
        ("Releases", "releases"),
        ("Recordings", "recordings"),
        ("Credits", "credits"),
        ("Place relationships", "places"),
        ("Excluded release groups", "exclusions"),
    ):
        lines.append(f"| {label} | {summary[key]} |")

    lines.extend(["", "## Credits by scope", "", "| Scope | Count |", "|---|---:|"])
    for scope, count in coverage["credits_by_scope"].items():
        lines.append(f"| {scope} | {count} |")
    if not coverage["credits_by_scope"]:
        lines.append("| none | 0 |")

    lines.extend(["", "## Credits by role", "", "| Role | Count |", "|---|---:|"])
    for role, count in coverage["credits_by_role"].items():
        lines.append(f"| {role} | {count} |")
    if not coverage["credits_by_role"]:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Coverage by subgenre",
            "",
            "| Subgenre | Bands | Bands with producer | Albums | "
            "Albums with producer | Releases | Recordings | Credits | Exclusions |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, stats in coverage["subgenres"].items():
        lines.append(
            f"| {name} | {stats['bands']} | {stats['bands_with_producer']} | "
            f"{stats['release_groups']} | {stats['albums_with_producer']} | "
            f"{stats['releases']} | {stats['recordings']} | {stats['credits']} | "
            f"{stats['exclusions']} |"
        )
    if not coverage["subgenres"]:
        lines.append("| none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |")

    lines.extend(
        [
            "",
            "## Coverage by decade",
            "",
            "| Decade | Bands | Bands with producer | Albums | Albums with producer | Releases |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, stats in coverage["decades"].items():
        lines.append(
            f"| {name} | {stats['bands']} | {stats['bands_with_producer']} | "
            f"{stats['release_groups']} | {stats['albums_with_producer']} | "
            f"{stats['releases']} |"
        )
    if not coverage["decades"]:
        lines.append("| unknown | 0 | 0 | 0 | 0 | 0 |")

    lines.extend(
        [
            "",
            "## Exclusions by reason",
            "",
            "| Reason | Count |",
            "|---|---:|",
        ]
    )
    for reason, count in coverage["exclusions_by_reason"].items():
        lines.append(f"| {reason} | {count} |")
    if not coverage["exclusions_by_reason"]:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Per-band coverage",
            "",
            "| Band | Subgenre | QID | Albums | Releases | Recordings | "
            "Credits | Producer coverage | Exclusions |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for band in coverage["bands"]:
        lines.append(
            f"| {band['name']} | {band['subgenre']} | "
            f"{'yes' if band['has_wikidata_qid'] else 'no'} | "
            f"{band['release_groups']} | {band['releases']} | {band['recordings']} | "
            f"{band['credits']} | {band['albums_with_producer']} | {band['exclusions']} |"
        )

    lines.extend(["", "## Run counters", ""])
    counters = coverage["run"]["counters"]
    if counters:
        lines.extend(["| Counter | Value |", "|---|---:|"])
        for key, value in sorted(counters.items()):
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("No run counters were supplied.")

    lines.extend(["", "## Failures", ""])
    failures = coverage["run"]["failures"]
    if failures:
        lines.extend(
            [
                "| Band | Phase | Type | Attempts | Message |",
                "|---|---|---|---:|---|",
            ]
        )
        for failure in failures:
            lines.append(
                f"| {failure.get('band_mbid') or 'unknown'} | "
                f"{failure.get('phase') or 'unknown'} | "
                f"{failure.get('error_type') or 'unknown'} | "
                f"{failure.get('attempts') or 0} | "
                f"{failure.get('message') or ''} |"
            )
    else:
        lines.append("No recorded failures.")

    return "\n".join(lines) + "\n"


def write_report(
    output_dir: Path,
    extractions: Iterable[BandExtraction],
    **context: Any,
) -> ReportResult:
    coverage = build_coverage(extractions, **context)
    markdown = render_report(coverage)
    output_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = output_dir / COVERAGE_FILE
    report_path = output_dir / REPORT_FILE
    coverage_path.write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(markdown, encoding="utf-8")
    return ReportResult(coverage_path, report_path, coverage)


def _new_group_stats() -> dict[str, Any]:
    return {
        "release_groups": 0,
        "albums_with_producer": 0,
        "releases": 0,
        "recordings": 0,
        "credits": 0,
        "places": 0,
        "exclusions": 0,
        "_band_ids": set(),
        "_bands_with_producer": set(),
        "_bands_with_qid": set(),
    }


def _add_band_stats(
    stats: dict[str, Any],
    extraction: BandExtraction,
    *,
    albums_with_producer: int,
    producer_groups: set[str],
    qid_present: bool,
    exclusion_count: int,
    release_group: str | None = None,
    release_count: int = 0,
) -> None:
    if release_group is None:
        stats["release_groups"] += len(extraction.release_groups)
        stats["releases"] += len(extraction.releases)
        stats["recordings"] += len(extraction.recordings)
        stats["credits"] += len(extraction.credits)
        stats["places"] += len(extraction.places)
        stats["exclusions"] += exclusion_count
        stats["albums_with_producer"] += albums_with_producer
    else:
        stats["release_groups"] += 1
        stats["releases"] += release_count
        if release_group in producer_groups:
            stats["albums_with_producer"] += 1

    stats["_band_ids"].add(extraction.band_mbid)
    if release_group is None:
        if albums_with_producer:
            stats["_bands_with_producer"].add(extraction.band_mbid)
    elif release_group in producer_groups:
        stats["_bands_with_producer"].add(extraction.band_mbid)
    if qid_present:
        stats["_bands_with_qid"].add(extraction.band_mbid)


def _drop_internal_sets(stats: dict[str, Any]) -> None:
    for key in ("_band_ids", "_bands_with_producer", "_bands_with_qid"):
        stats.pop(key, None)


def _sorted_stats(stats: dict[str, Any]) -> dict[str, Any]:
    return {key: stats[key] for key in sorted(stats)}


def _producer_groups(extraction: BandExtraction) -> set[str]:
    release_to_group = {release.mbid: release.release_group_mbid for release in extraction.releases}
    recording_to_groups: defaultdict[str, set[str]] = defaultdict(set)
    for link in extraction.release_recordings:
        group = release_to_group.get(link.release_mbid)
        if group:
            recording_to_groups[link.recording_mbid].add(group)

    groups: set[str] = set()
    for credit in extraction.credits:
        if credit.role not in PRODUCER_ROLES:
            continue
        if credit.release_group_mbid:
            groups.add(credit.release_group_mbid)
        elif credit.release_mbid and credit.release_mbid in release_to_group:
            groups.add(release_to_group[credit.release_mbid])
        elif credit.recording_mbid:
            groups.update(recording_to_groups.get(credit.recording_mbid, set()))
    return groups


def _decade(value: str | None) -> str:
    if not isinstance(value, str) or not value[:4].isdigit():
        return "unknown"
    year = int(value[:4])
    if 1980 <= year <= 1989:
        return "1980s"
    if 1990 <= year <= 1999:
        return "1990s"
    if year == 2000:
        return "2000"
    return "unknown"


def _decade_order(value: str) -> tuple[int, str]:
    order = {"1980s": 0, "1990s": 1, "2000": 2, "unknown": 3}
    return order.get(value, 4), value


def _datetime_string(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value
