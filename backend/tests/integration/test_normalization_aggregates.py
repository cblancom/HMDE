from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import (
    ArtistSubgenre,
    ArtistSubgenreClassification,
    IngestRun,
    NormalizationIssue,
    RawResponse,
)
from hmde.normalization.aggregates import derive_band_aggregates
from hmde.normalization.classification import classify_albums
from hmde.normalization.entities import normalize_entities
from hmde.normalization.inputs import TagMapInput, validate_inputs
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
BAND_MBID = "11111111-1111-4111-8111-111111111111"


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


def test_band_aggregate_refreshes_current_projection(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            inputs, run, index = _setup(session)
            classify_albums(session, inputs, index, run_id=run.id)
            result = derive_band_aggregates(
                session,
                inputs,
                index,
                run_id=run.id,
                seed_subgenres={BAND_MBID: "heavy-metal"},
            )

            assert result.counts.bands == 1
            assert result.counts.accepted == 1
            assert result.counts.review == 0
            assert result.counts.missing == 0
            artist_id = index.artists[BAND_MBID]
            history = session.scalar(
                select(ArtistSubgenreClassification).where(
                    ArtistSubgenreClassification.artist_id == artist_id
                )
            )
            current = session.scalar(
                select(ArtistSubgenre).where(ArtistSubgenre.artist_id == artist_id)
            )
            assert history is not None
            assert history.subgenre_code == "heavy-metal"
            assert history.is_primary is True
            assert history.status == "accepted"
            assert current is not None
            assert current.subgenre_code == "heavy-metal"
            assert current.taxonomy_version == "0.2.0"
            assert current.mapping_rule == "album-majority"
            session.rollback()
    finally:
        engine.dispose()


def test_unclassified_band_uses_seed_fallback(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            inputs, run, index = _setup(session)
            empty_tag_map = TagMapInput(
                version="0.1.0",
                taxonomy_version="0.2.0",
                path=inputs.tag_map.path,
                rules=(),
            )
            classify_albums(
                session,
                replace(inputs, tag_map=empty_tag_map),
                index,
                run_id=run.id,
            )
            result = derive_band_aggregates(
                session,
                inputs,
                index,
                run_id=run.id,
                seed_subgenres={BAND_MBID: "doom-metal"},
            )

            assert result.counts.review == 1
            assert result.counts.fallback == 1
            artist_id = index.artists[BAND_MBID]
            history = session.scalar(
                select(ArtistSubgenreClassification).where(
                    ArtistSubgenreClassification.artist_id == artist_id
                )
            )
            assert history is not None
            assert history.subgenre_code == "doom-metal"
            assert history.status == "review"
            assert history.confidence == 0.5
            assert history.mapping_rule == "seed-fallback"
            issues = session.scalar(select(func.count()).select_from(NormalizationIssue))
            assert issues is not None and issues >= 1
            session.rollback()
    finally:
        engine.dispose()
