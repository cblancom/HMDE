"""Deterministic UUID helpers for normalized rows."""

from __future__ import annotations

import uuid

HMDE_NAMESPACE = uuid.UUID("6f8f4f5c-4d3e-4b7d-9e2a-0c5b8d9a1f27")


def stable_uuid(kind: str, key: str) -> uuid.UUID:
    if not kind or not key:
        raise ValueError("kind and key are required for stable UUIDs")
    return uuid.uuid5(HMDE_NAMESPACE, f"{kind}:{key}")
