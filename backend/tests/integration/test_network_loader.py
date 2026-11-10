from __future__ import annotations

import uuid
from datetime import UTC, datetime

from hmde.models import (
    NormalizationRun,
    QualityRuleCatalogue,
    QualityRun,
    TaxonomyVersion,
)
from hmde.network.loader import load_network_data


def test_load_network_data_from_fixtures(seeded_session_factory) -> None:
    with seeded_session_factory() as session:
        session.merge(
            TaxonomyVersion(
                version="0.2.0",
                source_hash="a" * 64,
                source_path="data/taxonomy.json",
                is_current=True,
            )
        )
        session.merge(
            QualityRuleCatalogue(
                version="0.1.0",
                schema_version=1,
                source_hash="c" * 64,
                source_path="data/quality/rules-v0.1.0.json",
            )
        )
        session.flush()
        normalization = NormalizationRun(
            id=uuid.uuid4(),
            dataset_version="fixture-test",
            manifest_sha256="b" * 64,
            seed_list_version="0.2.0",
            taxonomy_version="0.2.0",
            tag_map_version="0.1.0",
            overrides_version="0.1.0",
            status="completed",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            code_version="test",
        )
        session.add(normalization)
        session.flush()
        quality = QualityRun(
            id=uuid.uuid4(),
            normalization_run_id=normalization.id,
            dataset_version="fixture-test",
            taxonomy_version="0.2.0",
            catalogue_version="0.1.0",
            code_version="test",
            status="completed_with_findings",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            parameters={},
            counters={},
        )
        session.add(quality)
        session.flush()

        data = load_network_data(session, quality_run=quality)
        assert data.albums
        assert data.producer_albums
        assert {row.album_id for row in data.producer_albums} <= set(data.albums)
        assert all(
            row.support_ratio is None or 0.0 <= row.support_ratio <= 1.0
            for row in data.producer_albums
        )
        assert data.quality.missing_dates >= 0
        assert data.quality.active_exceptions >= 0
        session.rollback()
