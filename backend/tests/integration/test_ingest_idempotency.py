from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete, func, select

from hmde.core.config import Settings
from hmde.etl.musicbrainz.cli import IngestOptions
from hmde.etl.musicbrainz.pipeline import IngestPipeline
from hmde.etl.musicbrainz.seed import SeedBand, SeedList
from hmde.models import Artist, Credit, IngestError, IngestRun, RawResponse, ReleaseGroup

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "musicbrainz"
BASE_URL = "https://mb.test/ws/2/"
ARTIST = "11111111-1111-4111-8111-111111111111"
RG1 = "22222222-2222-4222-8222-222222222222"
REL1 = "44444444-4444-4444-8444-444444444444"
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


def _options(tmp_path: Path, *, cache_only: bool = False, refresh: bool = False) -> IngestOptions:
    return IngestOptions(
        seed_list=tmp_path / "seed-list.json",
        output=tmp_path / "output",
        bands=(ARTIST,),
        max_bands=None,
        cache_only=cache_only,
        refresh=refresh,
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


def _handler(release_one: dict, *, fail_release_two: bool = False, call_log=None):
    def handle(request: httpx.Request) -> httpx.Response:
        if call_log is not None:
            call_log.append(request.url.path)
        path = request.url.path.removeprefix("/ws/2/")
        if path == f"artist/{ARTIST}":
            return httpx.Response(200, json=_load("artist"))
        if path == "release-group":
            return httpx.Response(200, json=_load("release_groups"))
        if path == "release":
            return httpx.Response(200, json=_load("releases"))
        if path == f"release/{REL1}":
            return httpx.Response(200, json=release_one)
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


def _run(
    session_factory,
    tmp_path: Path,
    handler,
    *,
    cache_only: bool = False,
    refresh: bool = False,
):
    return IngestPipeline(
        settings=_settings(),
        session_factory=session_factory,
        seed_list=_seed_list(),
        options=_options(tmp_path, cache_only=cache_only, refresh=refresh),
        code_version="test-version",
        http_client_factory=_factory(handler),
    ).run()


def _raw_count(session_factory) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(RawResponse)) or 0


def _canonical_counts(session_factory) -> tuple[int, int, int]:
    with session_factory() as session:
        return (
            session.scalar(select(func.count()).select_from(Artist)) or 0,
            session.scalar(select(func.count()).select_from(ReleaseGroup)) or 0,
            session.scalar(select(func.count()).select_from(Credit)) or 0,
        )


def test_rerun_reuses_raw_data_and_keeps_the_same_dataset(
    seeded_session_factory,
    tmp_path,
    run_cleanup,
) -> None:
    release_one = _load("release_1")
    canonical_before = _canonical_counts(seeded_session_factory)
    first = _run(seeded_session_factory, tmp_path, _handler(release_one))
    run_cleanup.append(first.run.run_id)
    assert first.dataset is not None
    first_version = first.dataset.dataset_version
    first_path = first.dataset.path
    raw_count = _raw_count(seeded_session_factory)

    def fail_network(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be used on a cached rerun")

    second = _run(seeded_session_factory, tmp_path, fail_network)
    run_cleanup.append(second.run.run_id)

    assert second.run.status == "completed"
    assert second.dataset is not None
    assert second.dataset.dataset_version == first_version
    assert second.dataset.path == first_path
    assert _raw_count(seeded_session_factory) == raw_count
    assert _canonical_counts(seeded_session_factory) == canonical_before
    with seeded_session_factory() as session:
        run = session.get(IngestRun, second.run.run_id)
        assert run is not None
        assert run.dataset_version == first_version
        assert run.counters["raw_responses_reused"] == 6
        assert run.counters["raw_responses_new"] == 0


def test_cache_only_replay_makes_no_network_requests(
    seeded_session_factory,
    tmp_path,
    run_cleanup,
) -> None:
    first = _run(seeded_session_factory, tmp_path, _handler(_load("release_1")))
    run_cleanup.append(first.run.run_id)

    def fail_network(request: httpx.Request) -> httpx.Response:
        raise AssertionError("cache-only must not use the network")

    replay = _run(
        seeded_session_factory,
        tmp_path,
        fail_network,
        cache_only=True,
    )
    run_cleanup.append(replay.run.run_id)

    assert replay.run.status == "completed"
    assert replay.dataset is not None
    assert replay.dataset.dataset_version == first.dataset.dataset_version


def test_refresh_creates_a_new_raw_response_and_dataset_version(
    seeded_session_factory,
    tmp_path,
    run_cleanup,
) -> None:
    release_one = _load("release_1")
    first = _run(seeded_session_factory, tmp_path, _handler(release_one))
    run_cleanup.append(first.run.run_id)
    raw_count = _raw_count(seeded_session_factory)

    changed_release_one = json.loads(json.dumps(release_one))
    changed_release_one["title"] = "Changed Edition"
    refreshed = _run(
        seeded_session_factory,
        tmp_path,
        _handler(changed_release_one),
        refresh=True,
    )
    run_cleanup.append(refreshed.run.run_id)

    assert refreshed.dataset is not None
    assert first.dataset is not None
    assert refreshed.dataset.dataset_version != first.dataset.dataset_version
    assert first.dataset.path.exists()
    assert _raw_count(seeded_session_factory) == raw_count + 1
    with seeded_session_factory() as session:
        run = session.get(IngestRun, refreshed.run.run_id)
        assert run is not None
        assert run.counters["raw_responses_new"] == 1
        assert run.counters["raw_responses_reused"] == 5
