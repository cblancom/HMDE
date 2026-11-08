"""Source-record creation from E3 raw responses."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import RawResponse, SourceRecord

from .errors import ProvenanceError
from .ids import stable_uuid


def ensure_source_records(
    session: Session,
    raw_response_ids: Iterable[uuid.UUID],
    *,
    dataset_version: str,
) -> dict[uuid.UUID, uuid.UUID]:
    wanted = set(raw_response_ids)
    if not wanted:
        return {}

    existing = {
        row.raw_response_id: row.id
        for row in session.scalars(
            select(SourceRecord).where(SourceRecord.raw_response_id.in_(wanted))
        )
    }
    missing = wanted - set(existing)
    if missing:
        raw_rows = {
            row.id: row
            for row in session.scalars(select(RawResponse).where(RawResponse.id.in_(missing)))
        }
        absent = missing - set(raw_rows)
        if absent:
            raise ProvenanceError(
                "missing raw_response rows for: " + ", ".join(str(item) for item in sorted(absent))
            )
        for raw_id in sorted(missing):
            raw = raw_rows[raw_id]
            source = SourceRecord(
                id=stable_uuid("source-record", str(raw.id)),
                source=raw.source,
                source_entity_type=raw.source_entity_type,
                external_id=raw.external_id,
                source_url=raw.request_url,
                fetched_at=raw.fetched_at,
                license=raw.license,
                payload_hash=raw.payload_hash,
                fixture_version=None,
                raw_response_id=raw.id,
                http_status=raw.http_status,
                api_version=raw.api_version,
                dataset_version=dataset_version,
                ingest_run_id=raw.first_ingest_run_id,
            )
            session.add(source)
            existing[raw.id] = source.id
    session.flush()
    return existing
