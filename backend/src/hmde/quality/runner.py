"""Quality run lifecycle and orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from hmde.models import QualityMetric, QualityRun

from .catalogue import RuleCatalogue, sync_catalogue
from .errors import QualityError
from .exceptions import evaluate_gate, load_exception_baseline, sync_exceptions
from .findings import persist_findings
from .inputs import QualityInputs
from .metrics import compute_metrics, persist_metrics
from .report import write_quality_report
from .structural import structural_findings


@dataclass(frozen=True, slots=True)
class QualityRunResult:
    run_id: uuid.UUID
    status: str
    counters: dict[str, int]
    report_path: str | None = None


def start_quality_run(
    session: Session,
    inputs: QualityInputs,
    *,
    code_version: str,
    modes: dict[str, object] | None = None,
) -> tuple[QualityRun, RuleCatalogue]:
    sync_catalogue(session, inputs.catalogue)
    run = QualityRun(
        id=uuid.uuid4(),
        normalization_run_id=inputs.normalization_run.id,
        dataset_version=inputs.normalization_run.dataset_version or "",
        taxonomy_version=inputs.normalization_run.taxonomy_version or "",
        catalogue_version=inputs.catalogue.version,
        code_version=code_version,
        status="running",
        parameters=modes or {},
        counters={},
    )
    session.add(run)
    session.flush()
    return run, inputs.catalogue


def finish_quality_run(
    session: Session,
    run: QualityRun,
    *,
    status: str,
    counters: dict[str, int],
    report_path: str | None = None,
) -> None:
    if status not in {"completed", "completed_with_findings", "blocked", "failed"}:
        raise QualityError(f"invalid terminal quality status: {status!r}")
    run.status = status
    run.finished_at = datetime.now(UTC)
    run.counters = counters
    run.report_path = report_path
    session.flush()


def run_quality(
    session: Session,
    inputs: QualityInputs,
    *,
    code_version: str,
    strict: bool,
    output_dir: Path | None = None,
) -> QualityRunResult:
    run, catalogue = start_quality_run(
        session,
        inputs,
        code_version=code_version,
        modes={"strict": strict},
    )
    rules = sync_catalogue(session, catalogue)
    baseline = load_exception_baseline(inputs.exceptions_path, catalogue)
    exceptions = sync_exceptions(session, baseline=baseline, rules=rules)
    findings = persist_findings(
        session,
        run=run,
        rules=rules,
        specs=structural_findings(session, normalization_run=inputs.normalization_run),
    )
    persist_metrics(
        session,
        quality_run_id=run.id,
        metrics=compute_metrics(session, inputs.normalization_run),
    )
    metrics = list(
        session.scalars(
            select(QualityMetric)
            .where(QualityMetric.quality_run_id == run.id)
            .order_by(QualityMetric.metric_code, QualityMetric.scope_type, QualityMetric.scope_key)
        )
    )
    gate = evaluate_gate(findings, rules=rules, exceptions=exceptions, strict=strict)
    counters = {
        "rules": len(rules),
        "findings": len(findings),
        "blocking_unexcepted": gate.blocking_unexcepted,
        "blocking_excepted": gate.blocking_excepted,
        "advisory": gate.advisory,
        "exceptions": len(exceptions),
        "metrics": len(metrics),
    }
    finish_quality_run(session, run, status=gate.status, counters=counters)
    report_path = None
    if output_dir is not None:
        report = write_quality_report(
            output_dir,
            run=run,
            rules=rules,
            findings=findings,
            exceptions=exceptions,
            metrics=metrics,
            gate=gate,
        )
        report_path = str(report.json_path)
        run.report_path = report_path
        session.flush()
    return QualityRunResult(
        run_id=run.id,
        status=run.status,
        counters=counters,
        report_path=report_path,
    )
