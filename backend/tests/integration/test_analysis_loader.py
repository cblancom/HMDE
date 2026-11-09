from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from hmde.analytics.catalogue import load_metric_catalogue
from hmde.analytics.loader import load_frames
from hmde.models import NormalizationRun, QualityRuleCatalogue, QualityRun, TaxonomyVersion

DATA = Path(__file__).resolve().parents[3] / "data"
TAXONOMY = DATA / "taxonomy.json"
CATALOGUE = DATA / "metrics" / "catalogue-v0.1.0.json"


def test_loader_returns_read_only_frames(seeded_session_factory) -> None:
    with seeded_session_factory() as session:
        session.add(
            TaxonomyVersion(
                version="0.2.0",
                source_hash="a" * 64,
                source_path="data/taxonomy.json",
                is_current=True,
            )
        )
        session.flush()
        normalization = NormalizationRun(
            id=uuid.uuid4(),
            dataset_version="mb-test",
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
        session.merge(
            QualityRuleCatalogue(
                version="0.1.0",
                schema_version=1,
                source_hash="c" * 64,
                source_path="data/quality/rules-v0.1.0.json",
            )
        )
        session.flush()
        quality = QualityRun(
            id=uuid.uuid4(),
            normalization_run_id=normalization.id,
            dataset_version="mb-test",
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
        frames = load_frames(
            session,
            normalization_run=normalization,
            quality_run=quality,
            taxonomy_path=TAXONOMY,
        )
        catalogue = load_metric_catalogue(CATALOGUE)

        assert catalogue.version == "0.1.0"
        assert not frames.bands.empty
        assert not frames.albums.empty
        assert not frames.credits.empty
        assert "aggregate_code" in frames.bands.columns
        assert "primary_code" in frames.albums.columns
        assert {"batch_id", "lifecycle", "count"} <= set(frames.membership.columns)
        assert frames.entity_counts["bands"] > 0
        assert frames.entity_counts["credits"] > 0
        session.rollback()
