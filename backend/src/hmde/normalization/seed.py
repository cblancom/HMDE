"""Seed-list membership loading for normalization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import InputValidationError


@dataclass(frozen=True, slots=True)
class SeedMember:
    name: str
    mbid: str
    seed_subgenre_code: str
    batch_id: str
    lifecycle: str


@dataclass(frozen=True, slots=True)
class SeedMembership:
    version: str
    bands: tuple[SeedMember, ...]


def load_seed_membership(path: Path) -> SeedMembership:
    payload, _ = _load_payload(path)
    version = _required(payload, "version")
    raw_bands = payload.get("bands")
    if not isinstance(raw_bands, list) or not raw_bands:
        raise InputValidationError("seed list must contain a non-empty bands array")
    bands: list[SeedMember] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_bands, start=1):
        if not isinstance(raw, dict):
            raise InputValidationError(f"seed band at position {index} must be an object")
        mbid = _required(raw, "mbid", position=index)
        if mbid in seen:
            raise InputValidationError(f"duplicate seed band MBID: {mbid}")
        lifecycle = _required(raw, "lifecycle", position=index)
        if lifecycle not in {"active", "retired"}:
            raise InputValidationError(f"seed band {mbid!r} has an invalid lifecycle")
        seen.add(mbid)
        bands.append(
            SeedMember(
                name=_required(raw, "name", position=index),
                mbid=mbid,
                seed_subgenre_code=_required(raw, "seed_subgenre_code", position=index),
                batch_id=_required(raw, "batch_id", position=index),
                lifecycle=lifecycle,
            )
        )
    return SeedMembership(version=version, bands=tuple(bands))


def _load_payload(path: Path) -> tuple[dict[str, Any], Path]:
    if not path.is_file():
        raise InputValidationError(f"seed list does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"could not read seed list: {path}") from exc
    if not isinstance(payload, dict):
        raise InputValidationError("seed list root must be an object")
    if "active_version" not in payload:
        return payload, path
    raw_target = _required(payload, "path")
    target = (path.parent / raw_target).resolve()
    if not target.is_relative_to(path.parent.resolve()):
        raise InputValidationError("active seed-list path escapes its directory")
    if not target.is_file():
        raise InputValidationError(f"active seed-list target does not exist: {target}")
    try:
        target_payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"could not read active seed list: {target}") from exc
    if not isinstance(target_payload, dict):
        raise InputValidationError("active seed-list target must be an object")
    if target_payload.get("version") != payload.get("active_version"):
        raise InputValidationError("active seed-list version mismatch")
    return target_payload, target


def _required(payload: dict[str, Any], key: str, *, position: int | None = None) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        location = f"seed band at position {position}" if position else "seed list"
        raise InputValidationError(f"{location} is missing a valid {key}")
    return value.strip()
