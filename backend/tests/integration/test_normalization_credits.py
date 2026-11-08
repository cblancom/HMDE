from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import Credit, IngestRun, RawResponse
from hmde.normalization.credits import normalize_credits
from hmde.normalization.entities import normalize_entities
from hmde.normalization.inputs import validate_inputs

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


def test_normalize_credits_preserves_scope_and_recording_context(
    test_database_url: str,
) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            _add_raw_responses(session)
            inputs = _inputs()
            index = normalize_entities(session, inputs)
            result = normalize_credits(session, inputs, index)

            assert result.counts.source_credits == 2
            assert result.counts.artists_created == 2
            assert result.counts.created == 2
            assert result.counts.reused == 0
            assert result.counts.expanded_contexts == 0
            assert result.counts.quarantined == 0

            group_id = index.release_groups["22222222-2222-4222-8222-222222222222"]
            recording_id = index.recordings["44444444-4444-4444-8444-444444444444"]
            credits = session.scalars(
                select(Credit).where(Credit.release_group_id == group_id)
            ).all()
            release_credit = next(credit for credit in credits if credit.scope == "release")
            recording_credit = next(credit for credit in credits if credit.scope == "recording")

            assert release_credit.role_code == "producer"
            assert release_credit.release_group_id == group_id
            assert release_credit.release_id is not None
            assert recording_credit.role_code == "engineer"
            assert recording_credit.release_group_id == group_id
            assert recording_credit.release_id is None
            assert recording_credit.recording_id == recording_id
            assert recording_credit.attributes == {
                "source_role": "engineer",
                "source_attributes": ["assistant"],
            }
            assert all(credit.source_record_id for credit in credits)
            session.rollback()
    finally:
        engine.dispose()


def test_normalize_credits_is_idempotent(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            _add_raw_responses(session)
            inputs = _inputs()
            index = normalize_entities(session, inputs)
            normalize_credits(session, inputs, index)
            before = session.scalar(select(func.count()).select_from(Credit))
            second = normalize_credits(session, inputs, index)

            assert second.counts.created == 0
            assert second.counts.artists_created == 0
            assert second.counts.reused == 2
            assert session.scalar(select(func.count()).select_from(Credit)) == before
            session.rollback()
    finally:
        engine.dispose()
