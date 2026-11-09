"""E6 metric computation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import pandas as pd

from .loader import AnalysisFrames


@dataclass(frozen=True, slots=True)
class AnalysisMetric:
    metric_code: str
    scope_type: str
    scope_key: str
    numerator: float
    denominator: float
    value: float
    unit: str
    details: dict[str, Any]


def distribution_metrics(frames: AnalysisFrames) -> list[AnalysisMetric]:
    metrics: list[AnalysisMetric] = []
    metrics.extend(_overview(frames))
    metrics.extend(_temporal(frames))
    metrics.extend(_taxonomy(frames))
    metrics.extend(_roles(frames))
    return metrics


def coverage_metrics(frames: AnalysisFrames) -> list[AnalysisMetric]:
    metrics: list[AnalysisMetric] = []
    total_albums = len(frames.albums)
    countries = Counter(frames.albums["artist_country"].fillna("unknown").replace("", "unknown"))
    metrics.extend(
        _metric("EDA-COV-001", "country", country, count, total_albums)
        for country, count in sorted(countries.items())
    )
    total_members = int(frames.membership["count"].sum()) if not frames.membership.empty else 0
    metrics.extend(
        _metric(
            "EDA-COV-002",
            "batch",
            str(row["batch_id"]),
            float(row["count"]),
            float(total_members),
            details={"lifecycle": row["lifecycle"]},
        )
        for row in frames.membership.to_dict("records")
    )
    total_sources = int(frames.sources["count"].sum()) if not frames.sources.empty else 0
    metrics.extend(
        _metric(
            "EDA-COV-003",
            "source",
            str(row["source"]),
            float(row["count"]),
            float(total_sources),
        )
        for row in frames.sources.to_dict("records")
    )
    return metrics


def limitation_metrics(frames: AnalysisFrames) -> list[AnalysisMetric]:
    metrics: list[AnalysisMetric] = []
    quality = frames.quality
    total_findings = int(quality["count"].sum()) if not quality.empty else 0
    exceptional = (
        int(quality.loc[quality["status"] == "exceptional", "count"].sum())
        if not quality.empty
        else 0
    )
    metrics.append(
        _metric(
            "EDA-LIM-001",
            "quality",
            "findings",
            exceptional,
            total_findings,
            details={
                "active_exceptions": frames.active_exceptions,
                "findings": quality.to_dict("records"),
            },
        )
    )
    checks = (
        ("album_date", frames.albums["first_release_date"].isna().sum(), len(frames.albums)),
        ("band_country", frames.bands["country"].isna().sum(), len(frames.bands)),
        ("band_wikidata_qid", frames.bands["qid"].isna().sum(), len(frames.bands)),
    )
    for field, missing, total in checks:
        metrics.append(
            _metric(
                "EDA-LIM-002",
                "field",
                field,
                int(missing),
                int(total),
                details={"meaning": "missing is not negative evidence"},
            )
        )
    return metrics


def producer_metrics(frames: AnalysisFrames) -> list[AnalysisMetric]:
    credits = frames.credits[
        frames.credits["role_code"].isin(("producer", "co-producer"))
        & frames.credits["release_group_id"].notna()
    ]
    counts = (
        credits.groupby(["artist_id", "artist_name"])["release_group_id"]
        .nunique()
        .sort_values(ascending=False)
    )
    total = int(counts.sum())
    metrics = [
        _metric(
            "EDA-PROD-001",
            "producer",
            str(name),
            int(count),
            total,
            details={"artist_id": str(artist_id), "minimum_albums": 2},
        )
        for (artist_id, name), count in counts.items()
        if count >= 2
    ]
    if not total:
        return metrics
    shares = counts / total
    metrics.append(
        _metric(
            "EDA-CONC-001",
            "producer",
            "top10",
            int(counts.head(10).sum()),
            total,
            details={"k": 10, "producers": int(len(counts))},
        )
    )
    hhi = float((shares**2).sum())
    metrics.append(
        _metric(
            "EDA-CONC-002",
            "producer",
            "hhi",
            hhi,
            1.0,
            details={"producers": int(len(counts)), "denominator": "album assignments"},
        )
    )
    cumulative = shares.cumsum()
    required = int((cumulative < 0.5).sum()) + 1
    metrics.append(
        AnalysisMetric(
            metric_code="EDA-CONC-003",
            scope_type="producer",
            scope_key="to_50_percent",
            numerator=float(required),
            denominator=1.0,
            value=float(required),
            unit="count",
            details={"producers": int(len(counts))},
        )
    )
    return metrics


def collaboration_metrics(frames: AnalysisFrames) -> list[AnalysisMetric]:
    credits = frames.credits.dropna(subset=["release_group_id", "artist_id"])
    names = credits.drop_duplicates("artist_id").set_index("artist_id")["artist_name"].to_dict()
    pair_counts: Counter[tuple[str, str]] = Counter()
    for _, album in credits.groupby("release_group_id"):
        artists = sorted(set(album["artist_id"]))
        pair_counts.update(combinations(artists, 2))
    qualifying = {pair: count for pair, count in pair_counts.items() if count >= 2}
    total = sum(qualifying.values())
    metrics = [
        _metric(
            "EDA-COLLAB-001",
            "pair",
            f"{names.get(first, first)} | {names.get(second, second)}",
            count,
            total,
            details={
                "artist_ids": [first, second],
                "minimum_shared_albums": 2,
                "warning": "descriptive co-occurrence, not influence or affinity",
            },
        )
        for (first, second), count in sorted(
            qualifying.items(), key=lambda item: (-item[1], item[0])
        )[:50]
    ]
    return metrics


def all_metrics(frames: AnalysisFrames) -> list[AnalysisMetric]:
    return (
        distribution_metrics(frames)
        + coverage_metrics(frames)
        + limitation_metrics(frames)
        + producer_metrics(frames)
        + collaboration_metrics(frames)
    )


def _overview(frames: AnalysisFrames) -> list[AnalysisMetric]:
    metrics = [
        _metric("EDA-CORPUS-001", "entity", key, count, count)
        for key, count in frames.entity_counts.items()
    ]
    for row in frames.membership.to_dict("records"):
        metrics.append(
            _metric(
                "EDA-CORPUS-002",
                "batch",
                str(row["batch_id"]),
                float(row["count"]),
                float(frames.membership["count"].sum()),
                details={"lifecycle": row["lifecycle"]},
            )
        )
    return metrics


def _temporal(frames: AnalysisFrames) -> list[AnalysisMetric]:
    albums = frames.albums.copy()
    albums["year"] = pd.to_datetime(albums["first_release_date"], errors="coerce").dt.year
    albums["decade"] = albums["year"].map(_decade)
    total = len(albums)
    metrics = [
        _metric("EDA-TIME-001", "decade", decade, count, total)
        for decade, count in sorted(Counter(albums["decade"]).items())
    ]
    metrics.extend(
        _metric("EDA-TIME-002", "precision", precision, count, total)
        for precision, count in sorted(
            Counter(albums["first_release_precision"].fillna("unknown")).items()
        )
    )
    return metrics


def _taxonomy(frames: AnalysisFrames) -> list[AnalysisMetric]:
    metrics: list[AnalysisMetric] = []
    taxonomy = frames.taxonomy.set_index("code")
    parent_name = {
        code: taxonomy.loc[parent, "name"] if parent in taxonomy.index else parent
        for code, parent in taxonomy["parent_code"].dropna().items()
    }
    parent_code = dict(taxonomy["parent_code"].dropna())
    primary = frames.albums["primary_code"].dropna()
    primary_total = len(primary)
    primary_counts = Counter(primary)
    for code, count in sorted(primary_counts.items()):
        metrics.append(_metric("EDA-TAX-001", "leaf", code, count, primary_total))
    family_counts = Counter(parent_code[code] for code in primary if code in parent_code)
    for family, count in sorted(family_counts.items()):
        metrics.append(
            _metric(
                "EDA-TAX-004",
                "family",
                family,
                count,
                primary_total,
                details={"family_name": parent_name.get(family, family)},
            )
        )
    aggregate = frames.bands["aggregate_code"].dropna()
    aggregate_total = len(aggregate)
    metrics.extend(
        _metric("EDA-TAX-002", "leaf", code, count, aggregate_total)
        for code, count in sorted(Counter(aggregate).items())
    )
    secondary = frames.secondary_labels["subgenre_code"].dropna()
    secondary_total = len(secondary)
    metrics.extend(
        _metric("EDA-TAX-003", "leaf", code, count, secondary_total)
        for code, count in sorted(Counter(secondary).items())
    )
    return metrics


def _roles(frames: AnalysisFrames) -> list[AnalysisMetric]:
    metrics: list[AnalysisMetric] = []
    total = len(frames.credits)
    for role, count in sorted(Counter(frames.credits["role_code"]).items()):
        metrics.append(_metric("EDA-ROLE-001", "role", role, count, total))
    for scope, count in sorted(Counter(frames.credits["scope"]).items()):
        metrics.append(_metric("EDA-ROLE-002", "scope", scope, count, total))
    return metrics


def _metric(
    code: str,
    scope_type: str,
    scope_key: str,
    numerator: float,
    denominator: float,
    *,
    details: dict[str, Any] | None = None,
) -> AnalysisMetric:
    return AnalysisMetric(
        metric_code=code,
        scope_type=scope_type,
        scope_key=scope_key,
        numerator=float(numerator),
        denominator=float(denominator),
        value=float(numerator) / float(denominator) if denominator else 0.0,
        unit="ratio",
        details=details or {},
    )


def _decade(year: float | int | None) -> str:
    if pd.isna(year):
        return "unknown"
    return f"{int(year) // 10 * 10}s"
