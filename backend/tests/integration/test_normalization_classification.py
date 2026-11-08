from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import IngestRun, NormalizationIssue, RawResponse, ReleaseGroupSubgenre
from hmde.normalization.classification import classify_albums
from hmde.normalization.entities import normalize_entities
from hmde.normalization.inputs import (
    ManualOverride,
    ManualOverridesInput,
    TagMapInput,
    TagMapRule,
    validate_inputs,
)
from hmde.normalization.pipeline import start_normalization_run
from hmde.normalization.taxonomy import sync_taxonomy

DATA = Path(__file__).resolve().parents[3] / "data"
MINI_DATASET = Path(__file__).resolve().parents[1] / "fixtures" / "normalization" / "mini-dataset"
TAXONOMY = DATA / "taxonomy.json"
TAG_MAP = DATA / "classifications" / "tag-map-v0.1.0.json"
OVERRIDES = DATA / "classifications" / "manual-overrides-v0.1.0.json"
RAW_IDS = (
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
)
RELEASE_GROUP_MBID = "22222222-2222-4222-8222-222222222222"


def _inputs():
    return validate_inputs(
        MINI_DATASET,
        taxonomy_path=TAXONOMY,
        tag_map_path=TAG_MAP,
        overrides_path=OVERRIDES,
    )


def _add_raw_responses(session: Session) -> None:
    run_id = uuid.uuid4()
    session.add(
        IngestRun(
            id=run_id,
            seed_list_version="0.2.0",
            status="completed",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            code_version="test",
        )
    )
    for index, raw_id in enumerate(RAW_IDS):
        session.add(
            RawResponse(
                id=uuid.UUID(raw_id),
                first_ingest_run_id=run_id,
                source="musicbrainz",
                source_entity_type="test",
                external_id=f"entity-{index}",
                request_key=f"{index:064d}",
                request_url=f"https://mb.test/{index}",
                request_params={},
                fetched_at=datetime.now(UTC),
                http_status=200,
                payload_hash=f"{index + 1:064d}",
                raw_path=f"raw/{index}.json",
                license="CC0-1.0",
                api_version="2",
            )
        )
    session.flush()


def _setup(session: Session):
    _add_raw_responses(session)
    inputs = _inputs()
    sync_taxonomy(session, TAXONOMY)
    run = start_normalization_run(session, inputs, code_version="test", mode="test")
    index = normalize_entities(session, inputs)
    return inputs, run, index


def test_high_confidence_album_is_accepted(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            inputs, run, index = _setup(session)
            result = classify_albums(session, inputs, index, run_id=run.id)

            assert result.counts.release_groups == 1
            assert result.counts.accepted == 1
            assert result.counts.review == 0
            assert result.counts.quarantined == 0
            rows = session.scalars(select(ReleaseGroupSubgenre)).all()
            assert len(rows) == 1
            assert rows[0].subgenre_code == "heavy-metal"
            assert rows[0].is_primary is True
            assert rows[0].status == "accepted"
            assert rows[0].mapping_rule == "tag-exact"
            assert session.scalar(select(func.count()).select_from(NormalizationIssue)) == 0
            session.rollback()
    finally:
        engine.dispose()


def test_medium_confidence_album_enters_review(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            inputs, run, index = _setup(session)
            tag_map = TagMapInput(
                version="0.1.0",
                taxonomy_version="0.2.0",
                path=inputs.tag_map.path,
                rules=(
                    TagMapRule(
                        source_label="heavy metal",
                        target_code="heavy-metal",
                        confidence=0.6,
                        priority=10,
                        mapping_rule="exact-label",
                    ),
                ),
            )
            result = classify_albums(
                session,
                replace(inputs, tag_map=tag_map),
                index,
                run_id=run.id,
            )

            assert result.counts.review == 1
            row = session.scalar(select(ReleaseGroupSubgenre))
            assert row is not None and row.status == "review"
            issue = session.scalar(select(NormalizationIssue))
            assert issue is not None and issue.severity == "medium"
            session.rollback()
    finally:
        engine.dispose()


def test_unmapped_album_is_quarantined(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            inputs, run, index = _setup(session)
            tag_map = TagMapInput(
                version="0.1.0",
                taxonomy_version="0.2.0",
                path=inputs.tag_map.path,
                rules=(),
            )
            result = classify_albums(
                session,
                replace(inputs, tag_map=tag_map),
                index,
                run_id=run.id,
            )

            assert result.counts.quarantined == 1
            assert session.scalar(select(func.count()).select_from(ReleaseGroupSubgenre)) == 0
            issue = session.scalar(select(NormalizationIssue))
            assert issue is not None and issue.issue_type == "classification_missing"
            session.rollback()
    finally:
        engine.dispose()


def test_override_takes_precedence(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            inputs, run, index = _setup(session)
            overrides = ManualOverridesInput(
                version="0.1.0",
                taxonomy_version="0.2.0",
                path=inputs.overrides.path,
                overrides=(
                    ManualOverride(
                        release_group_mbid=RELEASE_GROUP_MBID,
                        primary_code="hard-rock",
                        secondary_codes=("heavy-metal",),
                        confidence=1.0,
                        reason="reviewed",
                        reviewer="tester",
                        reviewed_at="2026-11-08",
                    ),
                ),
            )
            result = classify_albums(
                session,
                replace(inputs, overrides=overrides),
                index,
                run_id=run.id,
            )

            assert result.counts.overrides_applied == 1
            assert result.counts.accepted == 1
            rows = session.scalars(
                select(ReleaseGroupSubgenre).order_by(ReleaseGroupSubgenre.is_primary.desc())
            ).all()
            assert [(row.subgenre_code, row.is_primary) for row in rows] == [
                ("hard-rock", True),
                ("heavy-metal", False),
            ]
            assert all(row.mapping_rule == "override" for row in rows)
            session.rollback()
    finally:
        engine.dispose()


def test_classification_replay_is_idempotent(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            inputs, run, index = _setup(session)
            classify_albums(session, inputs, index, run_id=run.id)
            before = session.scalar(select(func.count()).select_from(ReleaseGroupSubgenre))
            classify_albums(session, inputs, index, run_id=run.id)
            after = session.scalar(select(func.count()).select_from(ReleaseGroupSubgenre))
            assert before == after == 1
            session.rollback()
    finally:
        engine.dispose()
