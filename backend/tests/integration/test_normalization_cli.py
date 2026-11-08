from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from hmde.models import (
    Artist,
    ArtistSubgenre,
    Credit,
    DatasetMembership,
    IngestRun,
    NormalizationRun,
    RawResponse,
    ReleaseGroupSubgenre,
)
from hmde.normalization.cli import NormalizationOptions, execute_normalization

DATA = Path(__file__).resolve().parents[3] / "data"
MINI_DATASET = Path(__file__).resolve().parents[1] / "fixtures" / "normalization" / "mini-dataset"
MINI_SEED_LIST = (
    Path(__file__).resolve().parents[1] / "fixtures" / "normalization" / "mini-seed-list.json"
)
TAXONOMY = DATA / "taxonomy.json"
TAG_MAP = DATA / "classifications" / "tag-map-v0.1.0.json"
OVERRIDES = DATA / "classifications" / "manual-overrides-v0.1.0.json"
RAW_IDS = (
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
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


def test_execute_normalization_runs_the_full_mini_pipeline(
    test_database_url: str,
    tmp_path: Path,
) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    options = NormalizationOptions(
        dataset=MINI_DATASET,
        taxonomy=TAXONOMY,
        tag_map=TAG_MAP,
        overrides=OVERRIDES,
        seed_list=MINI_SEED_LIST,
        output=tmp_path / "reports",
        dry_run=False,
    )
    try:
        with session_factory() as session:
            _add_raw_responses(session)
            result = execute_normalization(session, options, code_version="test-version")

            assert result.status == "completed"
            assert result.report_path is not None
            report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
            assert report["status"] == "completed"
            assert report["counts"]["membership"]["active"] == 1
            assert session.get(NormalizationRun, result.run_id) is not None
            assert session.scalar(select(func.count()).select_from(ReleaseGroupSubgenre)) == 1
            mini_artist = session.scalar(
                select(Artist).where(Artist.mbid == "11111111-1111-4111-8111-111111111111")
            )
            assert mini_artist is not None
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(ArtistSubgenre)
                    .where(ArtistSubgenre.artist_id == mini_artist.id)
                )
                == 1
            )
            assert session.scalar(select(func.count()).select_from(DatasetMembership)) == 1
            assert session.scalar(select(func.count()).select_from(Credit)) >= 2
            session.rollback()
    finally:
        engine.dispose()
