"""Immutable raw payload storage and request cache."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import RawResponse


class RawStoreError(Exception):
    """Base error for raw-store operations."""


class RawPayloadMissingError(RawStoreError):
    """The raw payload referenced by a database row is missing."""


class RawPayloadCorruptionError(RawStoreError):
    """The raw payload does not match its expected content hash."""


def hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_request_params(params: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            normalized[key] = None
        elif isinstance(value, (list, tuple)):
            normalized[key] = [str(item) for item in value]
        else:
            normalized[key] = str(value)
    return normalized


def build_request_key(
    method: str,
    url: str,
    params: Mapping[str, Any],
    api_version: str,
) -> str:
    canonical = {
        "api_version": api_version,
        "method": method.upper(),
        "params": normalize_request_params(params),
        "url": url,
    }
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hash_payload(encoded)


def write_raw_payload(root: Path, payload: bytes) -> tuple[str, str]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    digest = hash_payload(payload)
    relative_path = f"{digest}.json"
    target = root / relative_path

    if target.exists():
        existing = target.read_bytes()
        if hash_payload(existing) != digest:
            raise RawPayloadCorruptionError(
                f"existing raw payload does not match its content address: {target}"
            )
        return digest, relative_path

    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=root,
        prefix=f".{digest}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

    return digest, relative_path


def read_raw_payload(root: Path, relative_path: str, expected_hash: str) -> bytes:
    root = root.resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise RawPayloadCorruptionError("raw payload path escapes the raw root")
    if not path.is_file():
        raise RawPayloadMissingError(f"raw payload is missing: {path}")
    payload = path.read_bytes()
    if hash_payload(payload) != expected_hash:
        raise RawPayloadCorruptionError(f"raw payload hash mismatch: {path}")
    return payload


class RawStore:
    def __init__(self, session: Session, root: Path) -> None:
        self.session = session
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store_response(
        self,
        *,
        ingest_run_id: uuid.UUID,
        source: str,
        source_entity_type: str,
        external_id: str,
        method: str,
        request_url: str,
        request_params: Mapping[str, Any],
        fetched_at: datetime,
        http_status: int,
        body: bytes,
        license: str,
        api_version: str,
    ) -> RawResponse:
        request_key = build_request_key(method, request_url, request_params, api_version)
        payload_hash, raw_path = write_raw_payload(self.root, body)

        existing = self.session.scalar(
            select(RawResponse).where(
                RawResponse.request_key == request_key,
                RawResponse.payload_hash == payload_hash,
            )
        )
        if existing is not None:
            return existing

        raw_response = RawResponse(
            id=uuid.uuid4(),
            first_ingest_run_id=ingest_run_id,
            source=source,
            source_entity_type=source_entity_type,
            external_id=external_id,
            request_key=request_key,
            request_url=request_url,
            request_params=normalize_request_params(request_params),
            fetched_at=fetched_at,
            http_status=http_status,
            payload_hash=payload_hash,
            raw_path=raw_path,
            license=license,
            api_version=api_version,
        )
        self.session.add(raw_response)
        self.session.flush()
        return raw_response

    def get_cached(self, request_key: str) -> RawResponse | None:
        raw_response = self.session.scalar(
            select(RawResponse)
            .where(RawResponse.request_key == request_key)
            .order_by(RawResponse.fetched_at.desc(), RawResponse.id.desc())
            .limit(1)
        )
        if raw_response is None:
            return None
        self.read_payload(raw_response)
        return raw_response

    def read_payload(self, raw_response: RawResponse) -> bytes:
        return read_raw_payload(
            self.root,
            raw_response.raw_path,
            raw_response.payload_hash,
        )
