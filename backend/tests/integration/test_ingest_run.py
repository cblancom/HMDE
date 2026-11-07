from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select

from hmde.etl.musicbrainz.cli import IngestOptions, IngestRunner
from hmde.etl.musicbrainz.seed import SeedBand, SeedList, SeedListError
from hmde.models import IngestError, IngestRun


def _seed_list() -> SeedList:
    return SeedList(
        version="0.1.0",
        bands=(
            SeedBand(
                name="Band One",
                mbid=str(uuid.uuid4()),
                subgenre="Heavy Metal",
                country="GB",
                sequence=1,
            ),
            SeedBand(
                name="Band Two",
                mbid=str(uuid.uuid4()),
                subgenre="Thrash Metal",
                country="US",
                sequence=2,
            ),
        ),
    )


def _options(tmp_path: Path, **overrides) -> IngestOptions:
    values = {
        "seed_list": tmp_path / "seed-list.json",
        "output": tmp_path / "output",
        "bands": (),
        "max_bands": None,
        "cache_only": False,
        "refresh": False,
    }
    values.update(overrides)
    return IngestOptions(**values)


@pytest.fixture
def run_cleanup(seeded_session_factory):
    run_ids: list[uuid.UUID] = []
    yield run_ids
    with seeded_session_factory() as session:
        session.execute(delete(IngestError).where(IngestError.ingest_run_id.in_(run_ids)))
        session.execute(delete(IngestRun).where(IngestRun.id.in_(run_ids)))
        session.commit()


def test_runner_completes_all_bands(seeded_session_factory, tmp_path, run_cleanup) -> None:
    seed_list = _seed_list()
    seen: list[str] = []

    result = IngestRunner(
        session_factory=seeded_session_factory,
        seed_list=seed_list,
        options=_options(tmp_path),
        code_version="test",
    ).run(lambda session, band, run_id: seen.append(band.mbid))
    run_cleanup.append(result.run_id)

    assert result.status == "completed"
    assert result.processed_bands == 2
    assert result.failed_bands == 0
    assert seen == [band.mbid for band in seed_list.bands]

    with seeded_session_factory() as session:
        run = session.get(IngestRun, result.run_id)
        assert run is not None
        assert run.status == "completed"
        assert run.finished_at is not None
        assert run.counters["bands_total"] == 2
        assert run.counters["bands_processed"] == 2
        assert run.counters["bands_failed"] == 0
        assert run.parameters["seed_list_path"] == str(tmp_path / "seed-list.json")
        assert run.parameters["seed_list_version"] == "0.1.0"
        assert run.parameters["batch_ids"] == []


def test_failed_band_does_not_abort_the_run(
    seeded_session_factory,
    tmp_path,
    run_cleanup,
) -> None:
    seed_list = _seed_list()
    failed_mbid = seed_list.bands[1].mbid
    seen: list[str] = []

    def processor(session, band, run_id) -> None:
        seen.append(band.mbid)
        if band.mbid == failed_mbid:
            raise ValueError("synthetic band failure")

    result = IngestRunner(
        session_factory=seeded_session_factory,
        seed_list=seed_list,
        options=_options(tmp_path),
        code_version="test",
    ).run(processor)
    run_cleanup.append(result.run_id)

    assert result.status == "completed_with_errors"
    assert result.processed_bands == 1
    assert result.failed_bands == 1
    assert seen == [band.mbid for band in seed_list.bands]

    with seeded_session_factory() as session:
        run = session.get(IngestRun, result.run_id)
        assert run is not None
        assert run.counters["bands_failed"] == 1
        errors = session.scalars(
            select(IngestError).where(IngestError.ingest_run_id == result.run_id)
        ).all()
        assert len(errors) == 1
        assert errors[0].band_mbid == failed_mbid
        assert errors[0].error_type == "ValueError"
        assert errors[0].message == "synthetic band failure"


def test_subset_and_maximum_are_audited(seeded_session_factory, tmp_path, run_cleanup) -> None:
    seed_list = _seed_list()
    selected_mbid = seed_list.bands[0].mbid
    seen: list[str] = []

    result = IngestRunner(
        session_factory=seeded_session_factory,
        seed_list=seed_list,
        options=_options(tmp_path, bands=(selected_mbid,), max_bands=1),
        code_version="test",
    ).run(lambda session, band, run_id: seen.append(band.mbid))
    run_cleanup.append(result.run_id)

    assert seen == [selected_mbid]
    assert result.processed_bands == 1
    with seeded_session_factory() as session:
        run = session.get(IngestRun, result.run_id)
        assert run is not None
        assert run.counters["bands_total"] == 1
        assert run.parameters["bands"] == [selected_mbid]
        assert run.parameters["max_bands"] == 1


def test_unknown_band_is_rejected_before_writing_a_run(
    seeded_session_factory,
    tmp_path,
    run_cleanup,
) -> None:
    seed_list = _seed_list()
    with seeded_session_factory() as session:
        before = session.scalar(select(func.count()).select_from(IngestRun))

    with pytest.raises(SeedListError, match="not in the seed list"):
        IngestRunner(
            session_factory=seeded_session_factory,
            seed_list=seed_list,
            options=_options(tmp_path, bands=("00000000-0000-0000-0000-000000000099",)),
            code_version="test",
        ).run(lambda session, band, run_id: None)

    with seeded_session_factory() as session:
        after = session.scalar(select(func.count()).select_from(IngestRun))
    assert after == before
