"""Seed-list loading and validation."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_SEED_LIST_VERSION = "0.1.0"
EXPECTED_BAND_COUNT = 42
EXPECTED_SUBGENRES = {
    "Heavy Metal",
    "Thrash Metal",
    "Death Metal",
    "Black Metal",
    "Power Metal",
    "Doom Metal",
    "Progressive Metal",
}
EXPECTED_BANDS_PER_SUBGENRE = 6


class SeedListError(ValueError):
    """The seed list is missing, malformed or unsupported."""


@dataclass(frozen=True, slots=True)
class SeedBand:
    name: str
    mbid: str
    subgenre: str
    country: str
    sequence: int


@dataclass(frozen=True, slots=True)
class SeedList:
    version: str
    bands: tuple[SeedBand, ...]


def load_seed_list(path: Path) -> SeedList:
    if not path.is_file():
        raise SeedListError(f"seed list does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedListError(f"could not read seed list: {path}") from exc

    if not isinstance(payload, dict):
        raise SeedListError("seed list root must be a JSON object")

    version = payload.get("version")
    if version != SUPPORTED_SEED_LIST_VERSION:
        raise SeedListError(
            f"unsupported seed list version: {version!r}; expected {SUPPORTED_SEED_LIST_VERSION!r}"
        )

    raw_bands = payload.get("bands")
    if not isinstance(raw_bands, list):
        raise SeedListError("seed list must contain a bands array")
    if payload.get("total_bands") != EXPECTED_BAND_COUNT:
        raise SeedListError(
            f"seed list total_bands must be {EXPECTED_BAND_COUNT}, "
            f"got {payload.get('total_bands')!r}"
        )
    if len(raw_bands) != EXPECTED_BAND_COUNT:
        raise SeedListError(
            f"seed list must contain {EXPECTED_BAND_COUNT} bands, got {len(raw_bands)}"
        )

    bands: list[SeedBand] = []
    seen_mbids: set[str] = set()
    for index, raw_band in enumerate(raw_bands, start=1):
        if not isinstance(raw_band, dict):
            raise SeedListError(f"band at position {index} must be an object")

        name = _required_string(raw_band, "name", index)
        mbid = _required_string(raw_band, "mbid", index)
        subgenre = _required_string(raw_band, "subgenre", index)
        country = _required_string(raw_band, "country", index)
        status = _required_string(raw_band, "status", index)
        sequence = raw_band.get("sequence")

        if status != "verified":
            raise SeedListError(f"band {name!r} is not verified")
        try:
            mbid = str(uuid.UUID(mbid))
        except ValueError as exc:
            raise SeedListError(f"band {name!r} has an invalid MBID: {mbid!r}") from exc
        if mbid in seen_mbids:
            raise SeedListError(f"duplicate seed-list MBID: {mbid}")
        if subgenre not in EXPECTED_SUBGENRES:
            raise SeedListError(f"band {name!r} has an unknown subgenre: {subgenre!r}")
        if not isinstance(sequence, int) or sequence < 1:
            raise SeedListError(f"band {name!r} has an invalid sequence")

        seen_mbids.add(mbid)
        bands.append(
            SeedBand(
                name=name,
                mbid=mbid,
                subgenre=subgenre,
                country=country,
                sequence=sequence,
            )
        )

    distribution = Counter(band.subgenre for band in bands)
    if distribution != Counter({name: EXPECTED_BANDS_PER_SUBGENRE for name in EXPECTED_SUBGENRES}):
        raise SeedListError(
            "seed list must contain exactly "
            f"{EXPECTED_BANDS_PER_SUBGENRE} bands per subgenre; got {dict(distribution)}"
        )

    return SeedList(version=version, bands=tuple(bands))


def select_bands(
    seed_list: SeedList,
    band_mbids: tuple[str, ...],
    max_bands: int | None,
) -> tuple[SeedBand, ...]:
    if max_bands is not None and max_bands < 1:
        raise SeedListError("max_bands must be greater than zero")

    by_mbid = {band.mbid: band for band in seed_list.bands}
    if band_mbids:
        requested: set[str] = set()
        for mbid in band_mbids:
            try:
                requested.add(str(uuid.UUID(mbid)))
            except ValueError as exc:
                raise SeedListError(f"invalid requested band MBID: {mbid!r}") from exc
        missing = requested - set(by_mbid)
        if missing:
            raise SeedListError(
                "requested band MBID(s) are not in the seed list: " + ", ".join(sorted(missing))
            )
        selected = tuple(band for band in seed_list.bands if band.mbid in requested)
    else:
        selected = seed_list.bands

    if max_bands is not None:
        selected = selected[:max_bands]
    return selected


def _required_string(payload: dict[str, Any], key: str, position: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SeedListError(f"band at position {position} is missing a valid {key}")
    return value.strip()
