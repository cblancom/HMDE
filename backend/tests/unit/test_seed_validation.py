from __future__ import annotations

import json
from pathlib import Path

import pytest

from hmde.etl.musicbrainz.seed import (
    SeedBand,
    SeedList,
    SeedListError,
    load_seed_list,
    select_bands,
)

SEED_LIST_PATH = Path(__file__).resolve().parents[3] / "data" / "seed-list.json"


def _payload() -> dict:
    return json.loads(SEED_LIST_PATH.read_text(encoding="utf-8"))


def _write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "seed-list.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_seed_list_reads_the_versioned_dataset() -> None:
    seed_list = load_seed_list(SEED_LIST_PATH)

    assert seed_list.version == "0.1.0"
    assert len(seed_list.bands) == 42
    assert len({band.mbid for band in seed_list.bands}) == 42
    assert all(band.subgenre for band in seed_list.bands)
    assert all(band.country for band in seed_list.bands)


@pytest.mark.parametrize("version", [None, "0.0.0", 1])
def test_load_seed_list_rejects_unsupported_versions(tmp_path: Path, version) -> None:
    payload = _payload()
    payload["version"] = version

    with pytest.raises(SeedListError, match="version"):
        load_seed_list(_write_payload(tmp_path, payload))


def test_load_seed_list_rejects_duplicate_mbids(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][1]["mbid"] = payload["bands"][0]["mbid"]

    with pytest.raises(SeedListError, match="duplicate"):
        load_seed_list(_write_payload(tmp_path, payload))


def test_load_seed_list_rejects_unverified_bands(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"][0]["status"] = "pending"

    with pytest.raises(SeedListError, match="not verified"):
        load_seed_list(_write_payload(tmp_path, payload))


def test_load_seed_list_rejects_wrong_band_count(tmp_path: Path) -> None:
    payload = _payload()
    payload["bands"] = payload["bands"][:-1]

    with pytest.raises(SeedListError, match="42"):
        load_seed_list(_write_payload(tmp_path, payload))


def test_select_bands_supports_mbid_subset_and_maximum() -> None:
    seed_list = load_seed_list(SEED_LIST_PATH)
    first, second = seed_list.bands[0], seed_list.bands[1]

    selected = select_bands(seed_list, (second.mbid, first.mbid), 1)

    assert selected == (first,)
    assert select_bands(seed_list, (second.mbid,), None) == (second,)
    assert select_bands(seed_list, (), 2) == (first, second)


def test_select_bands_rejects_unknown_mbids() -> None:
    seed_list = SeedList(
        version="0.1.0",
        bands=(
            SeedBand(
                name="Test Band",
                mbid="00000000-0000-0000-0000-000000000001",
                subgenre="Heavy Metal",
                country="GB",
                sequence=1,
            ),
        ),
    )

    with pytest.raises(SeedListError, match="not in the seed list"):
        select_bands(seed_list, ("00000000-0000-0000-0000-000000000002",), None)
