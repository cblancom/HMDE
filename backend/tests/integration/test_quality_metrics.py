from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hmde.models import NormalizationRun
from hmde.quality.metrics import compute_metrics


def test_metrics_include_completeness_and_coverage(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with session_factory() as session:
            run = NormalizationRun(
                dataset_version="mb-test",
                taxonomy_version="0.2.0",
            )
            metrics = compute_metrics(session, run)
            by_code: dict[str, list] = {}
            for metric in metrics:
                by_code.setdefault(metric.metric_code, []).append(metric)

            assert {"Q-CMP-001", "Q-CMP-002", "Q-CMP-003", "Q-CMP-004"} <= set(by_code)
            assert "Q-COV-001" in by_code
            assert "Q-COV-002" in by_code
            assert {item.scope_type for item in by_code["Q-COV-001"]} >= {
                "decade",
                "role",
                "credit_scope",
                "country",
                "source",
            }
            assert all(0 <= item.value <= 1 for item in metrics)
            assert all(item.denominator >= 0 for item in metrics)
            assert by_code["Q-COV-002"][0].missing_count is not None
    finally:
        engine.dispose()
