from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import DatasetMembership, IngestRun, RawResponse
from hmde.normalization.entities import normalize_entities
from hmde.normalization.errors import ProvenanceError
from hmde.normalization.inputs import validate_inputs
from hmde.normalization.membership import sync_membership
from hmde.normalization.seed import SeedMember, SeedMembership

DATA = Path(__file__).resolve().parents[3] / "data"
MINI_DATASET = Path(__file__).resolve().parents[1] / "fixtures" / "normalization" / "mini-dataset"
TAXONOMY = DATA / "taxonomy.json"
TAG_MAP = DATA / "classifications" / "tag-map-v0.1.0.json"
OVERRIDES = DATA / "classifications" / "manual-overrides-v0.1.0.json"
BAND_MBID = "11111111-1111-4111-8111-111111111111"
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


def _seed_list(*, mbid: str = BAND_MBID) -> SeedMembership:
    return SeedMembership(
        version="0.2.0",
        bands=(
            SeedMember(
                name="Mini Band",
                mbid=mbid,
                seed_subgenre_code="heavy-metal",
                batch_id="v0.1.0",
                lifecycle="active",
            ),
        ),
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


def test_membership_syncs_active_band(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            _add_raw_responses(session)
            index = normalize_entities(session, _inputs())
            result = sync_membership(
                session,
                dataset_version="mini-20261108",
                seed_list=_seed_list(),
                artist_ids=index.artists,
            )

            assert result.created == 1
            assert result.active == 1
            row = session.scalar(select(DatasetMembership))
            assert row is not None
            assert row.dataset_version == "mini-20261108"
            assert row.batch_id == "v0.1.0"
            assert row.lifecycle == "active"
            assert row.added_in_version == "0.1.0"
            session.rollback()
    finally:
        engine.dispose()


def test_membership_rejects_unknown_band(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            with pytest.raises(ProvenanceError, match="not normalized"):
                sync_membership(
                    session,
                    dataset_version="mini-20261108",
                    seed_list=_seed_list(mbid="99999999-9999-4999-8999-999999999999"),
                    artist_ids={},
                )
            session.rollback()
    finally:
        engine.dispose()
