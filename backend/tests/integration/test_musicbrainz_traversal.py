from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete, select

from hmde.core.config import Settings
from hmde.etl.musicbrainz.client import MusicBrainzClient
from hmde.etl.musicbrainz.raw_store import RawStore
from hmde.etl.musicbrainz.seed import SeedBand
from hmde.etl.musicbrainz.traversal import MusicBrainzTraversal
from hmde.models import IngestError, IngestRun, RawResponse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "musicbrainz"
BASE_URL = "https://mb.test/ws/2/"
ARTIST = "11111111-1111-4111-8111-111111111111"
RG1 = "22222222-2222-4222-8222-222222222222"
RG2 = "33333333-3333-4333-8333-333333333333"
REL1 = "44444444-4444-4444-8444-444444444444"
REL2 = "55555555-5555-4555-8555-555555555555"
REC1 = "66666666-6666-4666-8666-666666666666"
REC2 = "77777777-7777-4777-8777-777777777777"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path.removeprefix("/ws/2/")
    if path == f"artist/{ARTIST}":
        return httpx.Response(200, json=_load("artist"))
    if path == "release-group":
        return httpx.Response(200, json=_load("release_groups"))
    if path == "release":
        return httpx.Response(200, json=_load("releases"))
    if path == f"release/{REL1}":
        return httpx.Response(200, json=_load("release_1"))
    if path == f"release/{REL2}":
        return httpx.Response(200, json=_load("release_2"))
    if path == f"recording/{REC1}":
        return httpx.Response(200, json=_load("recording_1"))
    if path == f"recording/{REC2}":
        return httpx.Response(200, json=_load("recording_2"))
    raise AssertionError(f"unexpected request: {request.url}")


class FakeLimiter:
    def __init__(self) -> None:
        self.calls = 0

    def wait(self) -> None:
        self.calls += 1


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde",
        musicbrainz_user_agent="HMDE/0.1 (test@example.test)",
        musicbrainz_base_url="https://mb.test/ws/2",
        musicbrainz_timeout_seconds=5.0,
        musicbrainz_min_interval_seconds=1.0,
    )


@pytest.fixture
def traversal_run(seeded_session_factory):
    run_id = uuid.uuid4()
    with seeded_session_factory() as session:
        session.add(
            IngestRun(
                id=run_id,
                seed_list_version="0.1.0",
                code_version="test",
            )
        )
        session.commit()
    try:
        yield run_id
    finally:
        with seeded_session_factory() as session:
            session.execute(delete(RawResponse).where(RawResponse.first_ingest_run_id == run_id))
            session.execute(delete(IngestError).where(IngestError.ingest_run_id == run_id))
            session.execute(delete(IngestRun).where(IngestRun.id == run_id))
            session.commit()


def test_traversal_persists_raw_responses_and_extracts_entities(
    seeded_session_factory,
    traversal_run,
    tmp_path,
) -> None:
    with seeded_session_factory() as session:
        raw_store = RawStore(session, tmp_path)
        http_client = httpx.Client(
            base_url=BASE_URL,
            transport=httpx.MockTransport(_handler),
        )
        client = MusicBrainzClient(
            settings=_settings(),
            raw_store=raw_store,
            ingest_run_id=traversal_run,
            http_client=http_client,
            rate_limiter=FakeLimiter(),  # type: ignore[arg-type]
        )
        extraction = MusicBrainzTraversal(client).extract_band(
            SeedBand(
                name="Test Band",
                mbid=ARTIST,
                subgenre="Heavy Metal",
                country="GB",
                sequence=1,
            )
        )
        session.commit()

        raw_rows = session.scalars(
            select(RawResponse).where(RawResponse.first_ingest_run_id == traversal_run)
        ).all()
        assert len(raw_rows) == 7
        raw_ids = {row.id for row in raw_rows}
        assert extraction.artist.raw_response_id in raw_ids
        assert all(group.raw_response_id in raw_ids for group in extraction.release_groups)
        assert all(release.raw_response_id in raw_ids for release in extraction.releases)
        assert all(recording.raw_response_id in raw_ids for recording in extraction.recordings)
        assert all(credit.raw_response_id in raw_ids for credit in extraction.credits)
        assert all(place.raw_response_id in raw_ids for place in extraction.places)

        assert len(extraction.release_groups) == 1
        assert extraction.exclusions[0].release_group_mbid == RG2
        assert {release.mbid for release in extraction.releases} == {REL1, REL2}
        assert {recording.mbid for recording in extraction.recordings} == {REC1, REC2}
        assert len(extraction.release_recordings) == 3
        assert len(extraction.credits) == 4
        assert len(extraction.places) == 2
