from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from hmde.models import Subgenre, TaxonomyNode, TaxonomyVersion
from hmde.normalization.errors import TaxonomyValidationError
from hmde.normalization.taxonomy import sync_taxonomy

TAXONOMY_PATH = Path(__file__).resolve().parents[3] / "data" / "taxonomy.json"


def test_sync_taxonomy_persists_version_nodes_and_projection(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            first = sync_taxonomy(session, TAXONOMY_PATH)
            second = sync_taxonomy(session, TAXONOMY_PATH)

            assert first.created is True
            assert second.created is False
            assert first.version == "0.2.0"
            assert first.node_count == 23
            assert first.leaf_count == 17
            assert session.scalar(select(func.count()).select_from(TaxonomyVersion)) == 1
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(TaxonomyNode)
                    .where(TaxonomyNode.taxonomy_version == "0.2.0")
                )
                == 23
            )
            current = session.scalar(
                select(TaxonomyVersion).where(TaxonomyVersion.is_current.is_(True))
            )
            assert current is not None
            assert current.version == "0.2.0"
            assert session.get(Subgenre, "heavy-metal") is not None
            assert session.get(Subgenre, "metal") is not None
            session.rollback()
    finally:
        engine.dispose()


def test_sync_taxonomy_rejects_version_content_drift(
    test_database_url: str,
    tmp_path: Path,
) -> None:
    payload = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    payload["nodes"][0]["name"] = "Changed Metal"
    changed = tmp_path / "taxonomy.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")

    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            sync_taxonomy(session, TAXONOMY_PATH)
            try:
                sync_taxonomy(session, changed)
            except TaxonomyValidationError as exc:
                assert "different content" in str(exc)
            else:
                raise AssertionError("expected taxonomy content drift to fail")
            session.rollback()
    finally:
        engine.dispose()
