from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from hmde.models import NormalizationRun, QualityException, QualityFinding, TaxonomyVersion
from hmde.quality.catalogue import sync_catalogue
from hmde.quality.exceptions import (
    evaluate_gate,
    load_exception_baseline,
    sync_exceptions,
)
from hmde.quality.findings import FindingSpec, persist_findings
from hmde.quality.inputs import load_quality_inputs
from hmde.quality.runner import start_quality_run

DATA = Path(__file__).resolve().parents[3] / "data"
CATALOGUE = DATA / "quality" / "rules-v0.1.0.json"
EXCEPTIONS = DATA / "quality" / "exceptions-v0.1.0.json"


def _setup(session):
    taxonomy = TaxonomyVersion(
        version="0.2.0",
        source_hash="a" * 64,
        source_path="data/taxonomy.json",
        is_current=True,
    )
    session.add(taxonomy)
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
    inputs = load_quality_inputs(
        session,
        normalization_run_id=normalization.id,
        rules_path=CATALOGUE,
        exceptions_path=EXCEPTIONS,
    )
    run, catalogue = start_quality_run(session, inputs, code_version="test")
    rules = sync_catalogue(session, catalogue)
    baseline = load_exception_baseline(EXCEPTIONS, catalogue)
    exceptions = sync_exceptions(session, baseline=baseline, rules=rules)
    return run, rules, baseline, exceptions


def test_exception_sync_and_gate(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            run, rules, baseline, exceptions = _setup(session)
            assert len(baseline.exceptions) == 58
            assert session.scalar(select(func.count()).select_from(QualityException)) == 58

            exception = next(item for item in baseline.exceptions if item.rule_code == "Q-CLS-001")
            findings = persist_findings(
                session,
                run=run,
                rules=rules,
                specs=[
                    FindingSpec(
                        rule_code=exception.rule_code,
                        entity_type=exception.entity_type,
                        entity_mbid=exception.entity_mbid,
                        entity_id=None,
                        observed_value={"status": "review"},
                        expected_value={"status": "accepted"},
                        details={},
                    )
                ],
            )
            gate = evaluate_gate(
                findings,
                rules=rules,
                exceptions=exceptions,
                strict=True,
            )
            assert gate.blocking_unexcepted == 0
            assert gate.blocking_excepted == 1
            assert gate.status == "completed_with_findings"
            assert findings[0].status == "exceptional"

            unknown = persist_findings(
                session,
                run=run,
                rules=rules,
                specs=[
                    FindingSpec(
                        rule_code="Q-CLS-001",
                        entity_type="release_group",
                        entity_mbid="99999999-9999-4999-8999-999999999999",
                        entity_id=None,
                        observed_value={"primary_labels": 0},
                        expected_value={"primary_labels": 1},
                        details={},
                    )
                ],
            )
            blocked = evaluate_gate(
                unknown,
                rules=rules,
                exceptions=exceptions,
                strict=True,
            )
            assert blocked.blocking_unexcepted == 1
            assert blocked.status == "blocked"
            assert session.scalar(select(func.count()).select_from(QualityFinding)) == 2
            session.rollback()
    finally:
        engine.dispose()
