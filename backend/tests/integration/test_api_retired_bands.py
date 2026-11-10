from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from hmde.models import (
    DatasetMembership,
    NormalizationRun,
    SourceRecord,
    TaxonomyVersion,
)


def test_retired_band_hidden_by_default_and_visible_by_direct_id(
    api_client,
    seeded_session_factory,
) -> None:
    band = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"}).json()["items"][0]
    source_id = uuid.uuid4()
    run_id = uuid.uuid4()
    dataset_version = f"retired-{uuid.uuid4().hex[:8]}"
    with seeded_session_factory() as session:
        session.merge(
            TaxonomyVersion(
                version="api-retired-taxonomy",
                source_hash="a" * 64,
                source_path="data/taxonomy.json",
                is_current=False,
            )
        )
        session.flush()
        session.add(
            SourceRecord(
                id=source_id,
                source="test",
                source_entity_type="artist",
                external_id=f"retired-{band['id']}",
                source_url="https://example.test/retired",
                fetched_at=datetime.now(UTC),
                license="test",
                payload_hash="test",
                fixture_version="test",
            )
        )
        session.add(
            NormalizationRun(
                id=run_id,
                dataset_version=dataset_version,
                manifest_sha256="b" * 64,
                seed_list_version="0.2.0",
                taxonomy_version="api-retired-taxonomy",
                tag_map_version="0.1.0",
                overrides_version="0.1.0",
                status="completed",
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC) + timedelta(days=1),
                code_version="test",
            )
        )
        session.add(
            DatasetMembership(
                dataset_version=dataset_version,
                artist_id=uuid.UUID(band["id"]),
                seed_list_version="0.2.0",
                batch_id="test",
                lifecycle="retired",
                added_in_version="0.2.0",
                retired_in_version="0.3.0",
                source_record_id=source_id,
            )
        )
        session.commit()
    try:
        default = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"})
        assert default.status_code == 200
        assert default.json()["total"] == 0

        included = api_client.get(
            "/api/v1/bands",
            params={"q": "Iron Maiden", "include_retired": True},
        )
        assert included.status_code == 200
        assert included.json()["total"] == 1

        detail = api_client.get(f"/api/v1/bands/{band['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Iron Maiden"
    finally:
        with seeded_session_factory() as session:
            session.execute(
                delete(DatasetMembership).where(
                    DatasetMembership.dataset_version == dataset_version
                )
            )
            session.execute(delete(NormalizationRun).where(NormalizationRun.id == run_id))
            session.execute(delete(SourceRecord).where(SourceRecord.id == source_id))
            session.commit()
