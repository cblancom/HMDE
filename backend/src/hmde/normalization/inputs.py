"""Validation of E3 datasets and versioned classification inputs."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .errors import InputValidationError
from .taxonomy import TaxonomyDocument, load_taxonomy_document

REQUIRED_DATASET_FILES = (
    "artists.ndjson",
    "release_groups.ndjson",
    "releases.ndjson",
    "recordings.ndjson",
    "release_recordings.ndjson",
    "credits.ndjson",
    "external_ids.ndjson",
)
EXPECTED_SEED_LIST_VERSION = "0.2.0"
EXPECTED_TAXONOMY_VERSION = "0.2.0"
EXPECTED_PERIOD_START = "1960-01-01"
EXPECTED_PERIOD_END = "2026-12-31"


@dataclass(frozen=True, slots=True)
class DatasetFile:
    name: str
    path: Path
    count: int
    sha256: str


@dataclass(frozen=True, slots=True)
class DatasetInput:
    root: Path
    manifest_path: Path
    dataset_version: str
    manifest_sha256: str
    seed_list_version: str
    taxonomy_version: str
    period_start: str
    period_end: str
    band_count: int
    batch_ids: tuple[str, ...]
    files: tuple[DatasetFile, ...]

    def file(self, name: str) -> DatasetFile:
        for entry in self.files:
            if entry.name == name:
                return entry
        raise InputValidationError(f"dataset does not contain {name!r}")


@dataclass(frozen=True, slots=True)
class TagMapRule:
    source_label: str
    target_code: str
    confidence: float
    priority: int
    mapping_rule: str


@dataclass(frozen=True, slots=True)
class TagMapInput:
    version: str
    taxonomy_version: str
    path: Path
    rules: tuple[TagMapRule, ...]


@dataclass(frozen=True, slots=True)
class ManualOverride:
    release_group_mbid: str
    primary_code: str
    secondary_codes: tuple[str, ...]
    confidence: float
    reason: str
    reviewer: str
    reviewed_at: str


@dataclass(frozen=True, slots=True)
class ManualOverridesInput:
    version: str
    taxonomy_version: str
    path: Path
    overrides: tuple[ManualOverride, ...]


@dataclass(frozen=True, slots=True)
class NormalizationInputs:
    dataset: DatasetInput
    taxonomy: TaxonomyDocument
    taxonomy_path: Path
    tag_map: TagMapInput
    overrides: ManualOverridesInput


def validate_inputs(
    dataset_path: Path,
    *,
    taxonomy_path: Path,
    tag_map_path: Path,
    overrides_path: Path,
) -> NormalizationInputs:
    dataset = load_dataset_input(dataset_path)
    taxonomy = load_taxonomy_document(taxonomy_path)
    if taxonomy.version != dataset.taxonomy_version:
        raise InputValidationError(
            f"taxonomy version mismatch: dataset {dataset.taxonomy_version!r}, "
            f"taxonomy {taxonomy.version!r}"
        )
    tag_map = load_tag_map(tag_map_path, taxonomy)
    overrides = load_manual_overrides(overrides_path, taxonomy)
    return NormalizationInputs(
        dataset=dataset,
        taxonomy=taxonomy,
        taxonomy_path=taxonomy_path,
        tag_map=tag_map,
        overrides=overrides,
    )


def load_dataset_input(root: Path) -> DatasetInput:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise InputValidationError(f"dataset manifest does not exist: {manifest_path}")
    raw_manifest = manifest_path.read_bytes()
    try:
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"could not read dataset manifest: {manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise InputValidationError("dataset manifest root must be an object")

    dataset_version = _required_string(manifest, "dataset_version")
    seed_list_version = _required_string(manifest, "seed_list_version")
    taxonomy_version = _required_string(manifest, "taxonomy_version")
    period_start = _required_string(manifest, "period_start")
    period_end = _required_string(manifest, "period_end")
    if seed_list_version != EXPECTED_SEED_LIST_VERSION:
        raise InputValidationError(
            f"unsupported seed-list version: {seed_list_version!r}; "
            f"expected {EXPECTED_SEED_LIST_VERSION!r}"
        )
    if taxonomy_version != EXPECTED_TAXONOMY_VERSION:
        raise InputValidationError(
            f"unsupported taxonomy version: {taxonomy_version!r}; "
            f"expected {EXPECTED_TAXONOMY_VERSION!r}"
        )
    if period_start != EXPECTED_PERIOD_START or period_end != EXPECTED_PERIOD_END:
        raise InputValidationError(
            f"unsupported period: {period_start!r} to {period_end!r}; "
            f"expected {EXPECTED_PERIOD_START!r} to {EXPECTED_PERIOD_END!r}"
        )
    band_count = manifest.get("band_count")
    if not isinstance(band_count, int) or band_count < 1:
        raise InputValidationError("dataset band_count must be a positive integer")
    batch_ids = manifest.get("batch_ids")
    if not isinstance(batch_ids, list) or not all(isinstance(item, str) for item in batch_ids):
        raise InputValidationError("dataset batch_ids must be an array of strings")

    raw_files = manifest.get("files")
    if not isinstance(raw_files, dict):
        raise InputValidationError("dataset manifest must contain a files object")
    files: list[DatasetFile] = []
    for name in REQUIRED_DATASET_FILES:
        entry = raw_files.get(name)
        if not isinstance(entry, dict):
            raise InputValidationError(f"dataset manifest is missing file metadata: {name}")
        path = root / name
        if not path.is_file():
            raise InputValidationError(f"dataset file does not exist: {path}")
        data = path.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        actual_count = data.count(b"\n")
        expected_hash = entry.get("sha256")
        expected_count = entry.get("count")
        if expected_hash != actual_hash:
            raise InputValidationError(f"dataset checksum mismatch: {name}")
        if expected_count != actual_count:
            raise InputValidationError(
                f"dataset line count mismatch for {name}: "
                f"manifest={expected_count!r}, file={actual_count}"
            )
        files.append(
            DatasetFile(
                name=name,
                path=path,
                count=actual_count,
                sha256=actual_hash,
            )
        )

    artists = next(item for item in files if item.name == "artists.ndjson")
    if artists.count != band_count:
        raise InputValidationError(
            f"dataset band_count does not match artists.ndjson: {band_count} != {artists.count}"
        )

    return DatasetInput(
        root=root,
        manifest_path=manifest_path,
        dataset_version=dataset_version,
        manifest_sha256=hashlib.sha256(raw_manifest).hexdigest(),
        seed_list_version=seed_list_version,
        taxonomy_version=taxonomy_version,
        period_start=period_start,
        period_end=period_end,
        band_count=band_count,
        batch_ids=tuple(batch_ids),
        files=tuple(files),
    )


def load_tag_map(path: Path, taxonomy: TaxonomyDocument) -> TagMapInput:
    payload = _read_object(path, "tag map")
    version = _required_string(payload, "version")
    taxonomy_version = _required_string(payload, "taxonomy_version")
    if taxonomy_version != taxonomy.version:
        raise InputValidationError(
            f"tag-map taxonomy version mismatch: {taxonomy_version!r} != {taxonomy.version!r}"
        )
    raw_rules = payload.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise InputValidationError("tag map must contain a non-empty rules array")
    rules: list[TagMapRule] = []
    seen: set[str] = set()
    for index, raw_rule in enumerate(raw_rules, start=1):
        if not isinstance(raw_rule, dict):
            raise InputValidationError(f"tag-map rule at position {index} must be an object")
        label = _required_string(raw_rule, "source_label", position=index)
        if label != label.casefold().strip():
            raise InputValidationError(f"tag-map source_label is not normalized: {label!r}")
        if label in seen:
            raise InputValidationError(f"duplicate tag-map source_label: {label!r}")
        target = _required_string(raw_rule, "target_code", position=index)
        if target not in taxonomy.assignable_leaves:
            raise InputValidationError(
                f"tag-map target is not an assignable taxonomy leaf: {target!r}"
            )
        confidence = raw_rule.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise InputValidationError(f"tag-map rule {label!r} has an invalid confidence")
        if not 0 <= float(confidence) <= 1:
            raise InputValidationError(f"tag-map rule {label!r} confidence is outside [0, 1]")
        priority = raw_rule.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool) or priority < 0:
            raise InputValidationError(f"tag-map rule {label!r} has an invalid priority")
        mapping_rule = _required_string(raw_rule, "mapping_rule", position=index)
        seen.add(label)
        rules.append(
            TagMapRule(
                source_label=label,
                target_code=target,
                confidence=float(confidence),
                priority=priority,
                mapping_rule=mapping_rule,
            )
        )
    return TagMapInput(
        version=version,
        taxonomy_version=taxonomy_version,
        path=path,
        rules=tuple(rules),
    )


def load_manual_overrides(path: Path, taxonomy: TaxonomyDocument) -> ManualOverridesInput:
    payload = _read_object(path, "manual overrides")
    version = _required_string(payload, "version")
    taxonomy_version = _required_string(payload, "taxonomy_version")
    if taxonomy_version != taxonomy.version:
        raise InputValidationError(
            f"override taxonomy version mismatch: {taxonomy_version!r} != {taxonomy.version!r}"
        )
    raw_overrides = payload.get("overrides")
    if not isinstance(raw_overrides, list):
        raise InputValidationError("manual overrides must contain an overrides array")
    overrides: list[ManualOverride] = []
    seen: set[str] = set()
    for index, raw_override in enumerate(raw_overrides, start=1):
        if not isinstance(raw_override, dict):
            raise InputValidationError(f"override at position {index} must be an object")
        mbid = _required_string(raw_override, "release_group_mbid", position=index)
        try:
            normalized_mbid = str(uuid.UUID(mbid))
        except ValueError as exc:
            raise InputValidationError(
                f"override at position {index} has an invalid release_group_mbid"
            ) from exc
        if normalized_mbid in seen:
            raise InputValidationError(f"duplicate override for release group: {normalized_mbid}")
        primary = _required_string(raw_override, "primary_code", position=index)
        if primary not in taxonomy.assignable_leaves:
            raise InputValidationError(f"override primary is not an assignable leaf: {primary!r}")
        raw_secondary = raw_override.get("secondary_codes", [])
        if not isinstance(raw_secondary, list) or not all(
            isinstance(item, str) for item in raw_secondary
        ):
            raise InputValidationError("override secondary_codes must be an array of strings")
        secondary = tuple(sorted(set(raw_secondary)))
        if len(secondary) != len(raw_secondary):
            raise InputValidationError("override secondary_codes must be unique")
        if primary in secondary:
            raise InputValidationError("override primary cannot also be secondary")
        if any(code not in taxonomy.assignable_leaves for code in secondary):
            raise InputValidationError("override secondary_codes contains a non-leaf code")
        confidence = raw_override.get("confidence")
        if confidence != 1.0:
            raise InputValidationError("override confidence must be 1.0")
        reason = _required_string(raw_override, "reason", position=index)
        reviewer = _required_string(raw_override, "reviewer", position=index)
        reviewed_at = _required_string(raw_override, "reviewed_at", position=index)
        try:
            date.fromisoformat(reviewed_at)
        except ValueError as exc:
            raise InputValidationError("override reviewed_at must be an ISO date") from exc
        seen.add(normalized_mbid)
        overrides.append(
            ManualOverride(
                release_group_mbid=normalized_mbid,
                primary_code=primary,
                secondary_codes=secondary,
                confidence=1.0,
                reason=reason,
                reviewer=reviewer,
                reviewed_at=reviewed_at,
            )
        )
    return ManualOverridesInput(
        version=version,
        taxonomy_version=taxonomy_version,
        path=path,
        overrides=tuple(overrides),
    )


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise InputValidationError(f"{label} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"could not read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise InputValidationError(f"{label} root must be a JSON object")
    return payload


def _required_string(
    payload: dict[str, Any],
    key: str,
    *,
    position: int | None = None,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        location = f"item at position {position}" if position else "input"
        raise InputValidationError(f"{location} is missing a valid {key}")
    return value.strip()
