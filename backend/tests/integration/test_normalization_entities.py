from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import (
    Artist,
    ExternalId,
    IngestRun,
    RawResponse,
    Recording,
    RecordingRelease,
    Release,
    ReleaseGroup,
    SourceRecord,
)
from hmde.normalization.entities import normalize_entities
from hmde.normalization.errors import ProvenanceError
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


def test_normalize_entities_creates_canonical_rows_and_provenance(
    test_database_url: str,
) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            _add_raw_responses(session)
            result = normalize_entities(session, _inputs())

            assert result.counts.artists_created == 1
            assert result.counts.release_groups_created == 1
            assert result.counts.releases_created == 1
            assert result.counts.recordings_created == 1
            assert result.counts.recording_releases_created == 1
            assert result.counts.external_ids_created == 1
            assert result.counts.source_records == 4

            artist = session.scalar(
                select(Artist).where(Artist.mbid == "11111111-1111-4111-8111-111111111111")
            )
            group = session.scalar(
                select(ReleaseGroup).where(
                    ReleaseGroup.mbid == "22222222-2222-4222-8222-222222222222"
                )
            )
            release = session.scalar(
                select(Release).where(Release.mbid == "33333333-3333-4333-8333-333333333333")
            )
            recording = session.scalar(
                select(Recording).where(Recording.mbid == "44444444-4444-4444-8444-444444444444")
            )
            link = session.scalar(
                select(RecordingRelease).where(
                    RecordingRelease.release_id == release.id,
                    RecordingRelease.recording_id == recording.id,
                )
            )
            source = session.scalar(
                select(SourceRecord).where(
                    SourceRecord.raw_response_id
                    == uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
                )
            )

            assert artist is not None and artist.type == "group"
            assert group is not None and group.artist_id == artist.id
            assert release is not None and release.release_group_id == group.id
            assert recording is not None
            assert link is not None and link.track_number == "1"
            assert source is not None and source.dataset_version == "mini-20261108"
            assert source.http_status == 200
            assert source.fixture_version is None
            assert result.recording_release_groups[
                "44444444-4444-4444-8444-444444444444"
            ] == frozenset({group.id})
            assert session.scalar(select(func.count()).select_from(ExternalId)) >= 1
            session.rollback()
    finally:
        engine.dispose()


def test_normalize_entities_is_idempotent(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            _add_raw_responses(session)
            inputs = _inputs()
            normalize_entities(session, inputs)
            session.flush()
            counts = {
                model.__tablename__: session.scalar(select(func.count()).select_from(model))
                for model in (Artist, ReleaseGroup, Release, Recording, RecordingRelease)
            }
            second = normalize_entities(session, inputs)

            assert second.counts.artists_created == 0
            assert second.counts.release_groups_created == 0
            assert second.counts.releases_created == 0
            assert second.counts.recordings_created == 0
            assert second.counts.recording_releases_created == 0
            assert counts == {
                model.__tablename__: session.scalar(select(func.count()).select_from(model))
                for model in (Artist, ReleaseGroup, Release, Recording, RecordingRelease)
            }
            session.rollback()
    finally:
        engine.dispose()


def test_missing_raw_response_fails_before_canonical_writes(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            before = session.scalar(select(func.count()).select_from(Artist))
            with pytest.raises(ProvenanceError, match="missing raw_response"):
                normalize_entities(session, _inputs())
            assert session.scalar(select(func.count()).select_from(Artist)) == before
            session.rollback()
    finally:
        engine.dispose()
