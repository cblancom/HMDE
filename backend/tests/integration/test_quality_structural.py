from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hmde.models import (
    Artist,
    ArtistSubgenreClassification,
    NormalizationRun,
    ReleaseGroup,
    ReleaseGroupSubgenre,
    SourceRecord,
    TaxonomyNode,
    TaxonomyVersion,
)
from hmde.quality.structural import structural_findings


def test_structural_rules_detect_classification_gaps(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            source_id = uuid.uuid4()
            session.add(
                SourceRecord(
                    id=source_id,
                    source="musicbrainz",
                    source_entity_type="artist",
                    external_id=str(uuid.uuid4()),
                    source_url="https://mb.test/artist",
                    fetched_at=datetime.now(UTC),
                    license="CC0-1.0",
                    payload_hash="a" * 64,
                    fixture_version=None,
                    dataset_version="mb-test",
                )
            )
            taxonomy_version = TaxonomyVersion(
                version="0.2.0",
                source_hash="a" * 64,
                source_path="data/taxonomy.json",
                is_current=True,
            )
            session.add(taxonomy_version)
            session.flush()
            session.add(
                TaxonomyNode(
                    taxonomy_version="0.2.0",
                    code="heavy-metal",
                    name="Heavy Metal",
                    parent_code=None,
                    assignable=True,
                    display_order=1,
                )
            )
            session.flush()
            artist = Artist(
                id=uuid.uuid4(),
                mbid="11111111-1111-4111-8111-111111111111",
                name="Quality Band",
                sort_name="Quality Band",
                type="group",
                country="GB",
                disambiguation=None,
                source_record_id=source_id,
            )
            session.add(artist)
            missing = ReleaseGroup(
                id=uuid.uuid4(),
                mbid="22222222-2222-4222-8222-222222222222",
                artist_id=artist.id,
                title="Missing Classification",
                first_release_date=date(2000, 1, 1),
                first_release_precision="year",
                primary_type="Album",
                secondary_types=[],
                disambiguation=None,
                source_record_id=source_id,
            )
            review = ReleaseGroup(
                id=uuid.uuid4(),
                mbid="33333333-3333-4333-8333-333333333333",
                artist_id=artist.id,
                title="Review Classification",
                first_release_date=date(2001, 1, 1),
                first_release_precision="year",
                primary_type="Album",
                secondary_types=[],
                disambiguation=None,
                source_record_id=source_id,
            )
            session.add_all((missing, review))
            session.flush()
            session.add(
                ReleaseGroupSubgenre(
                    release_group_id=review.id,
                    taxonomy_version="0.2.0",
                    subgenre_code="heavy-metal",
                    is_primary=True,
                    confidence=0.6,
                    status="review",
                    mapping_rule="tag-exact",
                    source_record_id=source_id,
                    evidence={},
                )
            )
            session.add(
                ArtistSubgenreClassification(
                    artist_id=artist.id,
                    taxonomy_version="0.2.0",
                    subgenre_code="heavy-metal",
                    is_primary=True,
                    confidence=0.5,
                    status="review",
                    mapping_rule="seed-fallback",
                    source_record_id=source_id,
                    evidence={},
                )
            )
            run = NormalizationRun(
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
            session.add(run)
            session.flush()

            findings = structural_findings(session, normalization_run=run)
            by_code: dict[str, list] = {}
            for finding in findings:
                by_code.setdefault(finding.rule_code, []).append(finding)

            assert missing.mbid in {finding.entity_mbid for finding in by_code["Q-CLS-001"]}
            assert len(by_code["Q-CLS-002"]) == 1
            assert by_code["Q-CLS-002"][0].entity_mbid == review.mbid
            assert len(by_code["Q-AGG-001"]) == 1
            assert by_code["Q-AGG-001"][0].entity_mbid == artist.mbid
            assert len(by_code["Q-MEM-001"]) == 1
            session.rollback()
    finally:
        engine.dispose()
