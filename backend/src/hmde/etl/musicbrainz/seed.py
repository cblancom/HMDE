"""Seed-list and taxonomy loading and validation."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSION = 2
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
LIFECYCLE_STATES = {"active", "retired"}


class SeedListError(ValueError):
    """The seed list is missing, malformed or unsupported."""


class TaxonomyError(SeedListError):
    """The taxonomy is missing, malformed or inconsistent."""


@dataclass(frozen=True, slots=True)
class TaxonomyNode:
    code: str
    name: str
    parent_code: str | None
    assignable: bool


@dataclass(frozen=True, slots=True)
class Taxonomy:
    version: str
    nodes: tuple[TaxonomyNode, ...]

    def node(self, code: str) -> TaxonomyNode | None:
        return next((node for node in self.nodes if node.code == code), None)

    def is_assignable(self, code: str) -> bool:
        node = self.node(code)
        return node is not None and node.assignable


@dataclass(frozen=True, slots=True)
class SeedBatch:
    batch_id: str
    version: str
    band_count: int
    status: str


@dataclass(frozen=True, slots=True)
class SeedBand:
    name: str
    mbid: str
    subgenre: str
    country: str
    sequence: int
    seed_subgenre_code: str | None = None
    batch_id: str | None = None
    lifecycle: str = "active"
    replaced_by_mbid: str | None = None
    verified_at: str | None = None

    @property
    def active(self) -> bool:
        return self.lifecycle == "active"


@dataclass(frozen=True, slots=True)
class SeedList:
    version: str
    bands: tuple[SeedBand, ...]
    schema_version: int = 1
    taxonomy_version: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    batches: tuple[SeedBatch, ...] = ()

    @property
    def active_bands(self) -> tuple[SeedBand, ...]:
        return tuple(band for band in self.bands if band.active)


def load_taxonomy(path: Path) -> Taxonomy:
    if not path.is_file():
        raise TaxonomyError(f"taxonomy does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaxonomyError(f"could not read taxonomy: {path}") from exc

    if not isinstance(payload, dict):
        raise TaxonomyError("taxonomy root must be a JSON object")
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        raise TaxonomyError("taxonomy is missing a valid version")
    raw_nodes = payload.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise TaxonomyError("taxonomy must contain a non-empty nodes array")

    nodes: list[TaxonomyNode] = []
    by_code: dict[str, TaxonomyNode] = {}
    for index, raw_node in enumerate(raw_nodes, start=1):
        if not isinstance(raw_node, dict):
            raise TaxonomyError(f"taxonomy node at position {index} must be an object")
        code = _required_taxonomy_string(raw_node, "code", index)
        name = _required_taxonomy_string(raw_node, "name", index)
        parent_code = raw_node.get("parent_code")
        if parent_code is not None and (
            not isinstance(parent_code, str) or not parent_code.strip()
        ):
            raise TaxonomyError(f"taxonomy node {code!r} has an invalid parent_code")
        assignable = raw_node.get("assignable")
        if not isinstance(assignable, bool):
            raise TaxonomyError(f"taxonomy node {code!r} must declare assignable as a boolean")
        if code in by_code:
            raise TaxonomyError(f"duplicate taxonomy code: {code}")
        node = TaxonomyNode(
            code=code,
            name=name,
            parent_code=parent_code.strip() if isinstance(parent_code, str) else None,
            assignable=assignable,
        )
        nodes.append(node)
        by_code[code] = node

    children: dict[str, int] = {code: 0 for code in by_code}
    for node in nodes:
        if node.parent_code is None:
            continue
        if node.parent_code not in by_code:
            raise TaxonomyError(
                f"taxonomy node {node.code!r} references unknown parent {node.parent_code!r}"
            )
        children[node.parent_code] += 1

    for node in nodes:
        if node.assignable and children[node.code]:
            raise TaxonomyError(f"taxonomy node {node.code!r} is assignable but has children")
        if not node.assignable and not children[node.code]:
            raise TaxonomyError(f"taxonomy leaf {node.code!r} must be assignable")

    for node in nodes:
        seen: set[str] = set()
        current: str | None = node.code
        while current is not None:
            if current in seen:
                raise TaxonomyError(f"taxonomy contains a parent cycle involving {node.code!r}")
            seen.add(current)
            current = by_code[current].parent_code

    return Taxonomy(version=version.strip(), nodes=tuple(nodes))


def load_seed_list(path: Path, *, taxonomy_path: Path | None = None) -> SeedList:
    payload, seed_path = _load_payload(path)
    schema_version = payload.get("schema_version")
    if schema_version is None:
        return _load_legacy_seed_list(payload)
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise SeedListError(
            f"unsupported seed-list schema_version: {schema_version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION!r}"
        )
    return _load_v2_seed_list(payload, seed_path, taxonomy_path)


def select_bands(
    seed_list: SeedList,
    band_mbids: tuple[str, ...],
    max_bands: int | None,
) -> tuple[SeedBand, ...]:
    if max_bands is not None and max_bands < 1:
        raise SeedListError("max_bands must be greater than zero")

    active_bands = seed_list.active_bands
    by_mbid = {band.mbid: band for band in active_bands}
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
        selected = tuple(band for band in active_bands if band.mbid in requested)
    else:
        selected = active_bands

    if max_bands is not None:
        selected = selected[:max_bands]
    return selected


def _load_payload(path: Path) -> tuple[dict[str, Any], Path]:
    payload = _read_json(path)
    if "active_version" not in payload:
        return payload, path

    active_version = _required_root_string(payload, "active_version")
    raw_path = _required_root_string(payload, "path")
    base = path.parent.resolve()
    target = (base / raw_path).resolve()
    if not target.is_relative_to(base):
        raise SeedListError(f"active seed-list path escapes its directory: {raw_path!r}")
    if not target.is_file():
        raise SeedListError(f"active seed-list target does not exist: {target}")

    target_payload = _read_json(target)
    target_version = target_payload.get("version")
    if target_version != active_version:
        raise SeedListError(
            f"active seed-list version mismatch: pointer {active_version!r}, "
            f"target {target_version!r}"
        )
    return target_payload, target


def _load_legacy_seed_list(payload: dict[str, Any]) -> SeedList:
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


def _load_v2_seed_list(
    payload: dict[str, Any],
    seed_path: Path,
    taxonomy_path: Path | None,
) -> SeedList:
    version = _required_root_string(payload, "version")
    taxonomy_version = _required_root_string(payload, "taxonomy_version")
    period_start = _required_date(payload, "period_start")
    period_end = _required_date(payload, "period_end")
    if period_start > period_end:
        raise SeedListError("seed-list period_start must not be after period_end")

    taxonomy = load_taxonomy(taxonomy_path or _infer_taxonomy_path(seed_path))
    if taxonomy.version != taxonomy_version:
        raise SeedListError(
            f"taxonomy version mismatch: seed list {taxonomy_version!r}, "
            f"taxonomy {taxonomy.version!r}"
        )

    batches = _load_batches(payload)
    batch_ids = {batch.batch_id for batch in batches}
    raw_bands = payload.get("bands")
    if not isinstance(raw_bands, list) or not raw_bands:
        raise SeedListError("seed list must contain a non-empty bands array")

    bands: list[SeedBand] = []
    seen_mbids: set[str] = set()
    seen_sequences: set[int] = set()
    for index, raw_band in enumerate(raw_bands, start=1):
        if not isinstance(raw_band, dict):
            raise SeedListError(f"band at position {index} must be an object")

        name = _required_string(raw_band, "name", index)
        mbid = _required_string(raw_band, "mbid", index)
        country = _required_string(raw_band, "country", index)
        status = _required_string(raw_band, "status", index)
        seed_subgenre_code = _required_string(raw_band, "seed_subgenre_code", index)
        batch_id = _required_string(raw_band, "batch_id", index)
        lifecycle = _required_string(raw_band, "lifecycle", index)
        verified_at = _required_string(raw_band, "verified_at", index)
        sequence = raw_band.get("sequence")
        replaced_by_mbid = raw_band.get("replaced_by_mbid")

        if status != "verified":
            raise SeedListError(f"band {name!r} is not verified")
        try:
            mbid = str(uuid.UUID(mbid))
        except ValueError as exc:
            raise SeedListError(f"band {name!r} has an invalid MBID: {mbid!r}") from exc
        if mbid in seen_mbids:
            raise SeedListError(f"duplicate seed-list MBID: {mbid}")
        if not isinstance(sequence, int) or sequence < 1:
            raise SeedListError(f"band {name!r} has an invalid sequence")
        if sequence in seen_sequences:
            raise SeedListError(f"duplicate seed-list sequence: {sequence}")
        if batch_id not in batch_ids:
            raise SeedListError(f"band {name!r} references unknown batch: {batch_id!r}")
        if lifecycle not in LIFECYCLE_STATES:
            raise SeedListError(f"band {name!r} has an invalid lifecycle: {lifecycle!r}")
        try:
            date.fromisoformat(verified_at)
        except ValueError as exc:
            raise SeedListError(
                f"band {name!r} has an invalid verified_at: {verified_at!r}"
            ) from exc

        node = taxonomy.node(seed_subgenre_code)
        if node is None or not node.assignable:
            raise SeedListError(
                f"band {name!r} seed_subgenre_code {seed_subgenre_code!r} "
                "is not an assignable taxonomy leaf"
            )

        replacement: str | None = None
        if replaced_by_mbid is not None:
            if not isinstance(replaced_by_mbid, str) or not replaced_by_mbid.strip():
                raise SeedListError(f"band {name!r} has an invalid replaced_by_mbid")
            try:
                replacement = str(uuid.UUID(replaced_by_mbid))
            except ValueError as exc:
                raise SeedListError(
                    f"band {name!r} has an invalid replaced_by_mbid: {replaced_by_mbid!r}"
                ) from exc
            if replacement == mbid:
                raise SeedListError(f"band {name!r} cannot replace itself")

        seen_mbids.add(mbid)
        seen_sequences.add(sequence)
        bands.append(
            SeedBand(
                name=name,
                mbid=mbid,
                subgenre=node.name,
                country=country,
                sequence=sequence,
                seed_subgenre_code=seed_subgenre_code,
                batch_id=batch_id,
                lifecycle=lifecycle,
                replaced_by_mbid=replacement,
                verified_at=verified_at,
            )
        )

    total_bands = payload.get("total_bands")
    if not isinstance(total_bands, int) or total_bands != len(bands):
        raise SeedListError(f"seed-list total_bands must equal {len(bands)}, got {total_bands!r}")

    expected_batch_counts = {batch.batch_id: batch.band_count for batch in batches}
    actual_batch_counts = Counter(band.batch_id for band in bands)
    if actual_batch_counts != Counter(expected_batch_counts):
        raise SeedListError(
            "seed-list batch counts do not match bands: "
            f"declared {expected_batch_counts}, actual {dict(actual_batch_counts)}"
        )

    distribution = payload.get("subgenre_distribution")
    if not isinstance(distribution, dict):
        raise SeedListError("seed list must contain a subgenre_distribution object")
    declared_distribution: dict[str, int] = {}
    for code, count in distribution.items():
        if not isinstance(code, str) or not isinstance(count, int) or count < 0:
            raise SeedListError("seed-list subgenre_distribution must map codes to counts")
        if not taxonomy.is_assignable(code):
            raise SeedListError(
                f"seed-list subgenre_distribution code {code!r} is not an assignable leaf"
            )
        declared_distribution[code] = count
    actual_distribution = Counter(band.seed_subgenre_code for band in bands)
    if Counter(declared_distribution) != actual_distribution:
        raise SeedListError(
            "seed-list subgenre_distribution does not match bands: "
            f"declared {declared_distribution}, actual {dict(actual_distribution)}"
        )

    return SeedList(
        version=version,
        bands=tuple(bands),
        schema_version=SUPPORTED_SCHEMA_VERSION,
        taxonomy_version=taxonomy_version,
        period_start=period_start,
        period_end=period_end,
        batches=batches,
    )


def _load_batches(payload: dict[str, Any]) -> tuple[SeedBatch, ...]:
    raw_batches = payload.get("batches")
    if not isinstance(raw_batches, list) or not raw_batches:
        raise SeedListError("seed list must contain a non-empty batches array")
    batches: list[SeedBatch] = []
    seen: set[str] = set()
    for index, raw_batch in enumerate(raw_batches, start=1):
        if not isinstance(raw_batch, dict):
            raise SeedListError(f"batch at position {index} must be an object")
        batch_id = _required_string(raw_batch, "batch_id", index)
        version = _required_string(raw_batch, "version", index)
        status = _required_string(raw_batch, "status", index)
        band_count = raw_batch.get("band_count")
        if batch_id in seen:
            raise SeedListError(f"duplicate batch id: {batch_id}")
        if not isinstance(band_count, int) or band_count < 1:
            raise SeedListError(f"batch {batch_id!r} has an invalid band_count")
        seen.add(batch_id)
        batches.append(
            SeedBatch(
                batch_id=batch_id,
                version=version,
                band_count=band_count,
                status=status,
            )
        )
    return tuple(batches)


def _infer_taxonomy_path(seed_path: Path) -> Path:
    for candidate in (
        seed_path.parent / "taxonomy.json",
        seed_path.parent.parent / "taxonomy.json",
    ):
        if candidate.is_file():
            return candidate
    raise SeedListError(f"could not locate taxonomy.json for seed list: {seed_path}")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SeedListError(f"seed list does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedListError(f"could not read seed list: {path}") from exc
    if not isinstance(payload, dict):
        raise SeedListError("seed list root must be a JSON object")
    return payload


def _required_root_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SeedListError(f"seed list is missing a valid {key}")
    return value.strip()


def _required_date(payload: dict[str, Any], key: str) -> date:
    value = _required_root_string(payload, key)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SeedListError(f"seed list has an invalid {key}: {value!r}") from exc


def _required_string(payload: dict[str, Any], key: str, position: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SeedListError(f"band at position {position} is missing a valid {key}")
    return value.strip()


def _required_taxonomy_string(payload: dict[str, Any], key: str, position: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TaxonomyError(f"taxonomy node at position {position} is missing a valid {key}")
    return value.strip()
