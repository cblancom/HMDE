"""Completeness and coverage quality metrics."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hmde.models import (
    Artist,
    ArtistSubgenre,
    ArtistSubgenreClassification,
    Credit,
    DatasetMembership,
    ExternalId,
    NormalizationRun,
    Recording,
    Release,
    ReleaseGroup,
    ReleaseGroupSubgenre,
    SourceRecord,
)

from .errors import QualityError


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_code: str
    dimension: str
    scope_type: str
    scope_key: str
    numerator: float
    denominator: float
    value: float
    unit: str
    missing_count: int | None
    details: dict[str, Any]


def compute_metrics(session: Session, run: NormalizationRun) -> list[MetricSpec]:
    taxonomy_version = run.taxonomy_version or ""
    metrics: list[MetricSpec] = []
    metrics.extend(_completeness(session, taxonomy_version))
    metrics.extend(_coverage(session, taxonomy_version, run.dataset_version or ""))
    return metrics


def persist_metrics(
    session: Session,
    *,
    quality_run_id: uuid.UUID,
    metrics: list[MetricSpec],
) -> None:
    from hmde.models import QualityMetric

    for metric in metrics:
        row = session.scalar(
            select(QualityMetric).where(
                QualityMetric.quality_run_id == quality_run_id,
                QualityMetric.metric_code == metric.metric_code,
                QualityMetric.scope_type == metric.scope_type,
                QualityMetric.scope_key == metric.scope_key,
            )
        )
        values = {
            "dimension": metric.dimension,
            "numerator": metric.numerator,
            "denominator": metric.denominator,
            "value": metric.value,
            "unit": metric.unit,
            "missing_count": metric.missing_count,
            "details": metric.details,
        }
        if row is None:
            session.add(
                QualityMetric(
                    id=uuid.uuid4(),
                    quality_run_id=quality_run_id,
                    metric_code=metric.metric_code,
                    scope_type=metric.scope_type,
                    scope_key=metric.scope_key,
                    **values,
                )
            )
        else:
            for name, value in values.items():
                setattr(row, name, value)
    session.flush()


def _completeness(session: Session, taxonomy_version: str) -> list[MetricSpec]:
    metrics: list[MetricSpec] = []
    provenance_pairs = []
    for model, column in (
        (Artist, Artist.source_record_id),
        (ReleaseGroup, ReleaseGroup.source_record_id),
        (Release, Release.source_record_id),
        (Recording, Recording.source_record_id),
        (Credit, Credit.source_record_id),
        (ReleaseGroupSubgenre, ReleaseGroupSubgenre.source_record_id),
        (ArtistSubgenreClassification, ArtistSubgenreClassification.source_record_id),
        (ArtistSubgenre, ArtistSubgenre.source_record_id),
        (DatasetMembership, DatasetMembership.source_record_id),
    ):
        total = session.scalar(select(func.count()).select_from(model)) or 0
        present = (
            session.scalar(select(func.count()).select_from(model).where(column.is_not(None))) or 0
        )
        provenance_pairs.append((present, total))
    present = sum(item[0] for item in provenance_pairs)
    total = sum(item[1] for item in provenance_pairs)
    metrics.append(_metric("Q-CMP-001", "completeness", "dataset", "provenance", present, total))

    albums = session.scalar(select(func.count()).select_from(ReleaseGroup)) or 0
    with_date = (
        session.scalar(
            select(func.count())
            .select_from(ReleaseGroup)
            .where(ReleaseGroup.first_release_date.is_not(None))
        )
        or 0
    )
    metrics.append(_metric("Q-CMP-002", "completeness", "dataset", "album_date", with_date, albums))

    band_ids = set(session.scalars(select(ArtistSubgenre.artist_id)))
    bands = len(band_ids)
    with_country = 0
    with_qid = 0
    if band_ids:
        countries = (
            session.scalar(
                select(func.count())
                .select_from(Artist)
                .where(Artist.id.in_(band_ids), Artist.country.is_not(None))
            )
            or 0
        )
        qids = (
            session.scalar(
                select(func.count(func.distinct(ExternalId.entity_id)))
                .select_from(ExternalId)
                .where(
                    ExternalId.entity_type == "artist",
                    ExternalId.source == "wikidata",
                    ExternalId.entity_id.in_(band_ids),
                )
            )
            or 0
        )
        with_country = countries
        with_qid = qids
    metrics.append(_metric("Q-CMP-003", "completeness", "field", "country", with_country, bands))
    metrics.append(_metric("Q-CMP-003", "completeness", "field", "wikidata_qid", with_qid, bands))

    producers = (
        session.scalar(
            select(func.count(func.distinct(Credit.release_group_id)))
            .select_from(Credit)
            .where(Credit.role_code.in_(("producer", "co-producer")))
        )
        or 0
    )
    metrics.append(_metric("Q-CMP-004", "completeness", "dataset", "producer", producers, albums))
    return metrics


def _coverage(session: Session, taxonomy_version: str, dataset_version: str) -> list[MetricSpec]:
    metrics: list[MetricSpec] = []
    album_dates = session.scalars(select(ReleaseGroup.first_release_date)).all()
    decades: Counter[str] = Counter(_decade(value) for value in album_dates)
    for decade, count in sorted(decades.items()):
        metrics.append(_metric("Q-COV-001", "coverage", "decade", decade, count, len(album_dates)))

    primary_codes = session.scalars(
        select(ReleaseGroupSubgenre.subgenre_code).where(
            ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
            ReleaseGroupSubgenre.is_primary.is_(True),
        )
    ).all()
    leaf_counts = Counter(primary_codes)
    for code, count in sorted(leaf_counts.items()):
        metrics.append(
            _metric("Q-COV-001", "coverage", "taxonomy_leaf", code, count, len(primary_codes))
        )

    roles = session.execute(select(Credit.role_code, func.count()).group_by(Credit.role_code)).all()
    total_credits = sum(count for _, count in roles)
    for role, count in sorted(roles):
        metrics.append(_metric("Q-COV-001", "coverage", "role", role, count, total_credits))

    scopes = session.execute(select(Credit.scope, func.count()).group_by(Credit.scope)).all()
    for scope, count in sorted(scopes):
        metrics.append(
            _metric("Q-COV-001", "coverage", "credit_scope", scope, count, total_credits)
        )

    countries = session.execute(
        select(Artist.country, func.count())
        .select_from(ReleaseGroup)
        .join(Artist, Artist.id == ReleaseGroup.artist_id)
        .group_by(Artist.country)
    ).all()
    total_albums = session.scalar(select(func.count()).select_from(ReleaseGroup)) or 0
    for country, count in sorted(countries, key=lambda item: (item[0] or "", item[1])):
        metrics.append(
            _metric("Q-COV-001", "coverage", "country", country or "unknown", count, total_albums)
        )

    sources = session.execute(
        select(SourceRecord.source, func.count()).group_by(SourceRecord.source)
    ).all()
    total_sources = sum(count for _, count in sources)
    for source, count in sorted(sources):
        metrics.append(_metric("Q-COV-001", "coverage", "source", source, count, total_sources))

    batches = session.execute(
        select(DatasetMembership.batch_id, func.count())
        .where(DatasetMembership.dataset_version == dataset_version)
        .group_by(DatasetMembership.batch_id)
    ).all()
    total_members = sum(count for _, count in batches)
    for batch, count in sorted(batches):
        metrics.append(_metric("Q-COV-001", "coverage", "batch", batch, count, total_members))

    missing_fields = 0
    missing_total = 0
    for value in album_dates:
        missing_total += 1
        if value is None:
            missing_fields += 1
    metrics.append(
        _metric(
            "Q-COV-002",
            "coverage",
            "dataset",
            "missing_album_dates",
            missing_fields,
            missing_total,
            missing_count=missing_fields,
            details={"meaning": "missing is not negative evidence"},
        )
    )
    return metrics


def _metric(
    code: str,
    dimension: str,
    scope_type: str,
    scope_key: str,
    numerator: float,
    denominator: float,
    *,
    missing_count: int | None = None,
    details: dict[str, Any] | None = None,
) -> MetricSpec:
    if denominator < 0:
        raise QualityError("metric denominator cannot be negative")
    value = numerator / denominator if denominator else 0.0
    return MetricSpec(
        metric_code=code,
        dimension=dimension,
        scope_type=scope_type,
        scope_key=scope_key,
        numerator=float(numerator),
        denominator=float(denominator),
        value=value,
        unit="ratio",
        missing_count=missing_count,
        details=details or {},
    )


def _decade(value: date | None) -> str:
    if value is None:
        return "unknown"
    return f"{value.year // 10 * 10}s"
