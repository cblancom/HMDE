from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from hmde.db.base import Base
from hmde.models import (
    ArtistSubgenre,
    ArtistSubgenreClassification,
    DatasetMembership,
    NormalizationIssue,
    NormalizationIssueAction,
    NormalizationRun,
    ReleaseGroupSubgenre,
    SourceRecord,
    TaxonomyNode,
    TaxonomyVersion,
)


def test_normalization_tables_are_registered() -> None:
    for model, table_name in (
        (TaxonomyVersion, "taxonomy_version"),
        (TaxonomyNode, "taxonomy_node"),
        (NormalizationRun, "normalization_run"),
        (NormalizationIssue, "normalization_issue"),
        (NormalizationIssueAction, "normalization_issue_action"),
        (ReleaseGroupSubgenre, "release_group_subgenre"),
        (ArtistSubgenreClassification, "artist_subgenre_classification"),
        (DatasetMembership, "dataset_membership"),
    ):
        assert model.__table__ is Base.metadata.tables[table_name]


def test_normalization_run_columns_and_constraints() -> None:
    table = NormalizationRun.__table__
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "dataset_version",
        "manifest_sha256",
        "seed_list_version",
        "taxonomy_version",
        "tag_map_version",
        "overrides_version",
        "status",
        "started_at",
        "finished_at",
        "code_version",
        "parameters",
        "counters",
        "report_path",
    } <= set(table.c.keys())
    assert {"ck_normalization_run_status", "ck_normalization_run_finished_at"} <= check_names
    assert table.c.taxonomy_version.foreign_keys


def test_taxonomy_version_has_single_current_index() -> None:
    indexes = {
        index.name: index for index in TaxonomyVersion.__table__.indexes if isinstance(index, Index)
    }

    assert "uq_taxonomy_version_current" in indexes
    assert indexes["uq_taxonomy_version_current"].unique
    assert indexes["uq_taxonomy_version_current"].dialect_options["postgresql"]["where"] is not None


def test_taxonomy_node_has_composite_key_and_parent_fk() -> None:
    table = TaxonomyNode.__table__

    assert [column.name for column in table.primary_key.columns] == [
        "taxonomy_version",
        "code",
    ]
    parent_fks = [fk for fk in table.foreign_keys if fk.parent.name == "parent_code"]
    assert len(parent_fks) == 1
    assert parent_fks[0].target_fullname == "taxonomy_node.code"


def test_classification_tables_have_primary_indexes() -> None:
    for model in (ReleaseGroupSubgenre, ArtistSubgenreClassification):
        index_names = {index.name for index in model.__table__.indexes if isinstance(index, Index)}
        assert any(name.endswith("_primary") for name in index_names)
        check_names = {
            constraint.name
            for constraint in model.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        assert any(name.endswith("_confidence") for name in check_names)


def test_source_record_adds_e3_provenance_and_nullable_fixture_version() -> None:
    table = SourceRecord.__table__
    unique_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert {
        "raw_response_id",
        "http_status",
        "api_version",
        "dataset_version",
        "ingest_run_id",
    } <= set(table.c.keys())
    assert table.c.fixture_version.nullable is True
    assert "uq_source_record_raw_response" in unique_names


def test_artist_subgenre_extends_current_projection() -> None:
    table = ArtistSubgenre.__table__
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "taxonomy_version",
        "status",
        "mapping_rule",
        "updated_at",
    } <= set(table.c.keys())
    assert "ck_artist_subgenre_status" in check_names


def test_dataset_membership_has_lifecycle_constraints() -> None:
    check_names = {
        constraint.name
        for constraint in DatasetMembership.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_dataset_membership_lifecycle",
        "ck_dataset_membership_retired",
    } <= check_names
