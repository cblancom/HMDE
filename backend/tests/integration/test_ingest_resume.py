from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete, select

from hmde.core.config import Settings
from hmde.etl.musicbrainz.cli import IngestOptions
from hmde.etl.musicbrainz.pipeline import IngestPipeline
from hmde.etl.musicbrainz.seed import SeedBand, SeedList
from hmde.models import IngestError, IngestRun, RawResponse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "musicbrainz"
BASE_URL = "https://mb.test/ws/2/"
ARTIST = "11111111-1111-4111-8111-111111111111"
REL2 = "55555555-5555-4555-8555-555555555555"
REC1 = "66666666-6666-4666-8666-666666666666"
REC2 = "77777777-7777-4777-8777-777777777777"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _seed_list() -> SeedList:
    return SeedList(
        version="0.1.0",
        bands=(
            SeedBand(
                name="Test Band",
                mbid=ARTIST,
                subgenre="Heavy Metal",
                country="GB",
                sequence=1,
            ),
        ),
    )


def _options(tmp_path: Path) -> IngestOptions:
    return IngestOptions(
        seed_list=tmp_path / "seed-list.json",
        output=tmp_path / "output",
        bands=(ARTIST,),
        max_bands=None,
        cache_only=False,
        refresh=False,
        raw_root=tmp_path / "raw",
    )


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde",
        musicbrainz_user_agent="HMDE/0.1 (test@example.test)",
        musicbrainz_base_url="https://mb.test/ws/2",
        musicbrainz_timeout_seconds=5.0,
        musicbrainz_min_interval_seconds=1.0,
    )


def _handler(*, fail_release_two: bool, calls: list[str]):
    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        path = request.url.path.removeprefix("/ws/2/")
        if path == f"artist/{ARTIST}":
            return httpx.Response(200, json=_load("artist"))
        if path == "release-group":
            return httpx.Response(200, json=_load("release_groups"))
        if path == "release":
            return httpx.Response(200, json=_load("releases"))
        if path == "release/44444444-4444-4444-8444-444444444444":
            return httpx.Response(200, json=_load("release_1"))
        if path == f"release/{REL2}":
            if fail_release_two:
                return httpx.Response(404, json={"error": "missing"})
            return httpx.Response(200, json=_load("release_2"))
        if path == f"recording/{REC1}":
            return httpx.Response(200, json=_load("recording_1"))
        if path == f"recording/{REC2}":
            return httpx.Response(200, json=_load("recording_2"))
        raise AssertionError(f"unexpected request: {request.url}")

    return handle


def _factory(handler):
    return lambda: httpx.Client(
        base_url=BASE_URL,
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
def run_cleanup(seeded_session_factory):
    run_ids: list[uuid.UUID] = []
    yield run_ids
    with seeded_session_factory() as session:
        session.execute(delete(RawResponse).where(RawResponse.first_ingest_run_id.in_(run_ids)))
        session.execute(delete(IngestError).where(IngestError.ingest_run_id.in_(run_ids)))
        session.execute(delete(IngestRun).where(IngestRun.id.in_(run_ids)))
        session.commit()


def _run(session_factory, tmp_path, handler):
    return IngestPipeline(
        settings=_settings(),
        session_factory=session_factory,
        seed_list=_seed_list(),
        options=_options(tmp_path),
        code_version="test-version",
        http_client_factory=_factory(handler),
    ).run()


def test_resume_reuses_partial_raw_responses_and_retries_missing_requests(
    seeded_session_factory,
    tmp_path,
    run_cleanup,
) -> None:
    first_calls: list[str] = []
    first = _run(
        seeded_session_factory,
        tmp_path,
        _handler(fail_release_two=True, calls=first_calls),
    )
    run_cleanup.append(first.run.run_id)

    assert first.run.status == "completed_with_errors"
    assert first.dataset is None
    with seeded_session_factory() as session:
        errors = session.scalars(
            select(IngestError).where(IngestError.ingest_run_id == first.run.run_id)
        ).all()
        assert len(errors) == 1
        raw_count = session.scalar(select(RawResponse.id).limit(1))
        assert raw_count is not None

    second_calls: list[str] = []
    second = _run(
        seeded_session_factory,
        tmp_path,
        _handler(fail_release_two=False, calls=second_calls),
    )
    run_cleanup.append(second.run.run_id)

    assert second.run.status == "completed"
    assert second.dataset is not None
    assert not any("/artist/" in path for path in second_calls)
    assert not any(path.endswith("/release-group") for path in second_calls)
    assert not any(path.endswith("/release") for path in second_calls)
    assert f"/release/{REL2}" in "".join(second_calls)
    assert any(path.endswith(f"/recording/{REC1}") for path in second_calls)
    assert any(path.endswith(f"/recording/{REC2}") for path in second_calls)
