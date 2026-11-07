from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from hmde.db.base import Base
from hmde.models import (
    Artist,
    ArtistSubgenre,
    Credit,
    ExternalId,
    FixtureLoad,
    Recording,
    RecordingRelease,
    Release,
    ReleaseGroup,
    Role,
    SourceRecord,
    Subgenre,
)


def test_expected_catalog_tables_are_registered() -> None:
    expected = {
        "artist",
        "artist_subgenre",
        "credit",
        "external_id",
        "fixture_load",
        "recording",
        "recording_release",
        "release",
        "release_group",
        "role",
        "source_record",
        "subgenre",
    }

    assert expected <= set(Base.metadata.tables)
    assert Artist.__table__ is Base.metadata.tables["artist"]
    assert ArtistSubgenre.__table__ is Base.metadata.tables["artist_subgenre"]
    assert Credit.__table__ is Base.metadata.tables["credit"]
    assert ExternalId.__table__ is Base.metadata.tables["external_id"]
    assert FixtureLoad.__table__ is Base.metadata.tables["fixture_load"]
    assert Recording.__table__ is Base.metadata.tables["recording"]
    assert RecordingRelease.__table__ is Base.metadata.tables["recording_release"]
    assert Release.__table__ is Base.metadata.tables["release"]
    assert ReleaseGroup.__table__ is Base.metadata.tables["release_group"]
    assert Role.__table__ is Base.metadata.tables["role"]
    assert SourceRecord.__table__ is Base.metadata.tables["source_record"]
    assert Subgenre.__table__ is Base.metadata.tables["subgenre"]


def test_artist_mbid_is_unique() -> None:
    assert Artist.__table__.c.mbid.unique is True


def test_credit_scope_constraints_are_registered() -> None:
    check_names = {
        constraint.name
        for constraint in Credit.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_credit_scope",
        "ck_credit_status",
        "ck_credit_confidence",
        "ck_credit_scope_target",
    } <= check_names


def test_external_id_and_recording_release_are_unique() -> None:
    external_id_uniques = {
        constraint.name
        for constraint in ExternalId.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    recording_release_uniques = {
        constraint.name
        for constraint in RecordingRelease.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_external_id_entity_source" in external_id_uniques
    assert "uq_recording_release" in recording_release_uniques
