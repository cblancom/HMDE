"""Read-only structural quality checks."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from hmde.models import (
    Artist,
    ArtistSubgenre,
    ArtistSubgenreClassification,
    Credit,
    DatasetMembership,
    NormalizationRun,
    Recording,
    Release,
    ReleaseGroup,
    ReleaseGroupSubgenre,
    TaxonomyNode,
)

from .findings import FindingSpec


def structural_findings(
    session: Session,
    *,
    normalization_run: NormalizationRun,
) -> list[FindingSpec]:
    findings: list[FindingSpec] = []
    findings.extend(_foreign_keys(session))
    findings.extend(_run_consistency(session, normalization_run))
    findings.extend(_provenance(session))
    findings.extend(_mbids(session))
    findings.extend(_taxonomy(session, normalization_run))
    findings.extend(_album_classifications(session, normalization_run))
    findings.extend(_band_aggregates(session, normalization_run))
    findings.extend(_credits(session))
    findings.extend(_membership(session, normalization_run))
    return findings


def _foreign_keys(session: Session) -> list[FindingSpec]:
    queries = (
        (
            "SELECT count(*) FROM release_group rg "
            "LEFT JOIN artist a ON a.id = rg.artist_id "
            "WHERE a.id IS NULL"
        ),
        (
            "SELECT count(*) FROM release r "
            "LEFT JOIN release_group g ON g.id = r.release_group_id "
            "WHERE g.id IS NULL"
        ),
        (
            "SELECT count(*) FROM recording_release rr "
            "LEFT JOIN release r ON r.id = rr.release_id "
            "LEFT JOIN recording rec ON rec.id = rr.recording_id "
            "WHERE r.id IS NULL OR rec.id IS NULL"
        ),
        (
            "SELECT count(*) FROM credit c "
            "LEFT JOIN artist a ON a.id = c.artist_id "
            "LEFT JOIN release_group g ON g.id = c.release_group_id "
            "WHERE a.id IS NULL OR g.id IS NULL"
        ),
        (
            "SELECT count(*) FROM release_group_subgenre x "
            "LEFT JOIN release_group g ON g.id = x.release_group_id "
            "WHERE g.id IS NULL"
        ),
        (
            "SELECT count(*) FROM artist_subgenre_classification x "
            "LEFT JOIN artist a ON a.id = x.artist_id "
            "WHERE a.id IS NULL"
        ),
        (
            "SELECT count(*) FROM dataset_membership x "
            "LEFT JOIN artist a ON a.id = x.artist_id "
            "WHERE a.id IS NULL"
        ),
    )
    total = sum(int(session.scalar(text(query)) or 0) for query in queries)
    if not total:
        return []
    return [
        FindingSpec(
            rule_code="Q-FK-001",
            entity_type="database",
            entity_mbid=None,
            entity_id=None,
            observed_value={"orphan_rows": total},
            expected_value={"orphan_rows": 0},
            details={},
        )
    ]


def _run_consistency(session: Session, run: NormalizationRun) -> list[FindingSpec]:
    valid = (
        run.status in {"completed", "completed_with_review"}
        and bool(run.dataset_version)
        and bool(run.taxonomy_version)
        and bool(run.seed_list_version)
    )
    if valid:
        return []
    return [
        FindingSpec(
            rule_code="Q-RUN-001",
            entity_type="normalization_run",
            entity_mbid=None,
            entity_id=run.id,
            observed_value={
                "status": run.status,
                "dataset_version": run.dataset_version,
                "taxonomy_version": run.taxonomy_version,
            },
            expected_value={"status": "completed", "versions": "present"},
            details={},
        )
    ]


def _provenance(session: Session) -> list[FindingSpec]:
    checks = [
        (Artist, "artist", Artist.source_record_id),
        (ReleaseGroup, "release_group", ReleaseGroup.source_record_id),
        (Release, "release", Release.source_record_id),
        (Recording, "recording", Recording.source_record_id),
        (Credit, "credit", Credit.source_record_id),
        (ReleaseGroupSubgenre, "release_group_subgenre", ReleaseGroupSubgenre.source_record_id),
        (
            ArtistSubgenreClassification,
            "artist_subgenre_classification",
            ArtistSubgenreClassification.source_record_id,
        ),
        (ArtistSubgenre, "artist_subgenre", ArtistSubgenre.source_record_id),
        (DatasetMembership, "dataset_membership", DatasetMembership.source_record_id),
    ]
    missing = sum(
        session.scalar(select(func.count()).select_from(model).where(column.is_(None))) or 0
        for model, _, column in checks
    )
    if not missing:
        return []
    return [
        FindingSpec(
            rule_code="Q-PROV-001",
            entity_type="database",
            entity_mbid=None,
            entity_id=None,
            observed_value={"rows_without_provenance": missing},
            expected_value={"rows_without_provenance": 0},
            details={"scope": [label for _, label, _ in checks]},
        )
    ]


def _mbids(session: Session) -> list[FindingSpec]:
    findings: list[FindingSpec] = []
    for model, label in (
        (Artist, "artist"),
        (ReleaseGroup, "release_group"),
        (Release, "release"),
        (Recording, "recording"),
    ):
        for (value,) in session.execute(select(model.mbid)):
            try:
                uuid.UUID(value)
            except ValueError:
                findings.append(
                    FindingSpec(
                        rule_code="Q-MBID-001",
                        entity_type=label,
                        entity_mbid=value,
                        entity_id=None,
                        observed_value={"mbid": value},
                        expected_value={"mbid": "valid UUID"},
                        details={},
                    )
                )
        duplicates = session.execute(
            select(model.mbid, func.count()).group_by(model.mbid).having(func.count() > 1)
        ).all()
        for value, count in duplicates:
            findings.append(
                FindingSpec(
                    rule_code="Q-MBID-002",
                    entity_type=label,
                    entity_mbid=value,
                    entity_id=None,
                    observed_value={"duplicates": count},
                    expected_value={"duplicates": 1},
                    details={},
                )
            )
    return findings


def _taxonomy(session: Session, run: NormalizationRun) -> list[FindingSpec]:
    findings: list[FindingSpec] = []
    taxonomy_version = run.taxonomy_version or ""
    for model, label, id_column in (
        (ReleaseGroupSubgenre, "release_group_subgenre", ReleaseGroupSubgenre.release_group_id),
        (
            ArtistSubgenreClassification,
            "artist_subgenre_classification",
            ArtistSubgenreClassification.artist_id,
        ),
        (ArtistSubgenre, "artist_subgenre", ArtistSubgenre.artist_id),
    ):
        rows = session.execute(
            select(model.subgenre_code, model.taxonomy_version, id_column)
            .outerjoin(
                TaxonomyNode,
                and_(
                    TaxonomyNode.taxonomy_version == model.taxonomy_version,
                    TaxonomyNode.code == model.subgenre_code,
                ),
            )
            .where(or_(TaxonomyNode.code.is_(None), TaxonomyNode.assignable.is_(False)))
        ).all()
        for code, node_version, entity_id in rows:
            findings.append(
                FindingSpec(
                    rule_code="Q-TAX-001",
                    entity_type=label,
                    entity_mbid=None,
                    entity_id=entity_id,
                    observed_value={"subgenre_code": code, "taxonomy_version": node_version},
                    expected_value={"assignable_leaf": True},
                    details={},
                )
            )
    for model, label in (
        (ReleaseGroupSubgenre, "release_group_subgenre"),
        (ArtistSubgenreClassification, "artist_subgenre_classification"),
        (ArtistSubgenre, "artist_subgenre"),
    ):
        count = (
            session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.taxonomy_version != taxonomy_version)
            )
            or 0
        )
        if count:
            findings.append(
                FindingSpec(
                    rule_code="Q-TAX-002",
                    entity_type=label,
                    entity_mbid=None,
                    entity_id=None,
                    observed_value={"different_taxonomy_version_rows": count},
                    expected_value={"taxonomy_version": taxonomy_version},
                    details={},
                )
            )
    return findings


def _album_classifications(
    session: Session,
    run: NormalizationRun,
) -> list[FindingSpec]:
    taxonomy_version = run.taxonomy_version or ""
    missing = session.scalars(
        select(ReleaseGroup)
        .outerjoin(
            ReleaseGroupSubgenre,
            and_(
                ReleaseGroupSubgenre.release_group_id == ReleaseGroup.id,
                ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
                ReleaseGroupSubgenre.is_primary.is_(True),
            ),
        )
        .where(ReleaseGroupSubgenre.release_group_id.is_(None))
    ).all()
    findings = [
        FindingSpec(
            rule_code="Q-CLS-001",
            entity_type="release_group",
            entity_mbid=group.mbid,
            entity_id=group.id,
            observed_value={"primary_labels": 0},
            expected_value={"primary_labels": 1},
            details={"title": group.title},
        )
        for group in missing
    ]
    review = session.execute(
        select(ReleaseGroupSubgenre, ReleaseGroup)
        .join(ReleaseGroup, ReleaseGroup.id == ReleaseGroupSubgenre.release_group_id)
        .where(
            ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
            ReleaseGroupSubgenre.is_primary.is_(True),
            ReleaseGroupSubgenre.status == "review",
        )
    ).all()
    findings.extend(
        FindingSpec(
            rule_code="Q-CLS-002",
            entity_type="release_group",
            entity_mbid=group.mbid,
            entity_id=row.release_group_id,
            observed_value={"status": row.status},
            expected_value={"status": "accepted"},
            details={"subgenre_code": row.subgenre_code, "title": group.title},
        )
        for row, group in review
    )
    duplicates = session.execute(
        select(ReleaseGroupSubgenre.release_group_id, func.count())
        .where(
            ReleaseGroupSubgenre.taxonomy_version == taxonomy_version,
            ReleaseGroupSubgenre.is_primary.is_(True),
        )
        .group_by(ReleaseGroupSubgenre.release_group_id)
        .having(func.count() > 1)
    ).all()
    findings.extend(
        FindingSpec(
            rule_code="Q-CLS-003",
            entity_type="release_group",
            entity_mbid=None,
            entity_id=group_id,
            observed_value={"primary_labels": count},
            expected_value={"primary_labels": 1},
            details={},
        )
        for group_id, count in duplicates
    )
    return findings


def _band_aggregates(session: Session, run: NormalizationRun) -> list[FindingSpec]:
    taxonomy_version = run.taxonomy_version or ""
    review = session.execute(
        select(ArtistSubgenreClassification, Artist)
        .join(Artist, Artist.id == ArtistSubgenreClassification.artist_id)
        .where(
            ArtistSubgenreClassification.taxonomy_version == taxonomy_version,
            ArtistSubgenreClassification.is_primary.is_(True),
            ArtistSubgenreClassification.status == "review",
        )
    ).all()
    findings = [
        FindingSpec(
            rule_code="Q-AGG-001",
            entity_type="artist",
            entity_mbid=artist.mbid,
            entity_id=row.artist_id,
            observed_value={"status": row.status, "confidence": row.confidence},
            expected_value={"status": "accepted"},
            details={"mapping_rule": row.mapping_rule, "name": artist.name},
        )
        for row, artist in review
    ]
    duplicates = session.execute(
        select(ArtistSubgenreClassification.artist_id, func.count())
        .where(
            ArtistSubgenreClassification.taxonomy_version == taxonomy_version,
            ArtistSubgenreClassification.is_primary.is_(True),
        )
        .group_by(ArtistSubgenreClassification.artist_id)
        .having(func.count() > 1)
    ).all()
    findings.extend(
        FindingSpec(
            rule_code="Q-AGG-002",
            entity_type="artist",
            entity_mbid=None,
            entity_id=artist_id,
            observed_value={"primary_aggregates": count},
            expected_value={"primary_aggregates": 1},
            details={},
        )
        for artist_id, count in duplicates
    )
    return findings


def _credits(session: Session) -> list[FindingSpec]:
    invalid = session.execute(
        select(Credit.id).where(
            or_(
                Credit.scope.notin_(("release_group", "release", "recording")),
                and_(
                    Credit.scope == "release_group",
                    or_(Credit.release_id.is_not(None), Credit.recording_id.is_not(None)),
                ),
                and_(
                    Credit.scope == "release",
                    or_(Credit.release_id.is_(None), Credit.recording_id.is_not(None)),
                ),
                and_(Credit.scope == "recording", Credit.recording_id.is_(None)),
            )
        )
    ).all()
    return [
        FindingSpec(
            rule_code="Q-CRD-001",
            entity_type="credit",
            entity_mbid=None,
            entity_id=credit_id,
            observed_value={"scope_target_valid": False},
            expected_value={"scope_target_valid": True},
            details={},
        )
        for (credit_id,) in invalid
    ]


def _membership(session: Session, run: NormalizationRun) -> list[FindingSpec]:
    active = (
        session.scalar(
            select(func.count())
            .select_from(DatasetMembership)
            .where(
                DatasetMembership.dataset_version == run.dataset_version,
                DatasetMembership.lifecycle == "active",
            )
        )
        or 0
    )
    if active == 57:
        return []
    return [
        FindingSpec(
            rule_code="Q-MEM-001",
            entity_type="dataset_membership",
            entity_mbid=None,
            entity_id=None,
            observed_value={"active_memberships": active},
            expected_value={"active_memberships": 57},
            details={"dataset_version": run.dataset_version},
        )
    ]
