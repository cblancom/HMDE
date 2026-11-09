"""Quality JSON and Markdown reports."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hmde.models import QualityException, QualityFinding, QualityMetric, QualityRule, QualityRun

from .exceptions import GateResult

REPORT_JSON = "report.json"
REPORT_MARKDOWN = "report.md"
INTERPRETATION = (
    "Missing data is not negative evidence: absence of a tag, mapping, credit, "
    "date or identifier means the source did not provide it in this dataset snapshot."
)


@dataclass(frozen=True, slots=True)
class QualityReportResult:
    json_path: Path
    markdown_path: Path
    data: dict[str, Any]


def write_quality_report(
    output_dir: Path,
    *,
    run: QualityRun,
    rules: dict[str, QualityRule],
    findings: list[QualityFinding],
    exceptions: dict[tuple[str, str, str | None], QualityException],
    metrics: list[QualityMetric],
    gate: GateResult,
) -> QualityReportResult:
    target = output_dir / str(run.id)
    target.mkdir(parents=True, exist_ok=True)
    data = _build_report(
        run=run,
        rules=rules,
        findings=findings,
        exceptions=exceptions,
        metrics=metrics,
        gate=gate,
    )
    json_path = target / REPORT_JSON
    markdown_path = target / REPORT_MARKDOWN
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render(data), encoding="utf-8")
    return QualityReportResult(json_path=json_path, markdown_path=markdown_path, data=data)


def _build_report(
    *,
    run: QualityRun,
    rules: dict[str, QualityRule],
    findings: list[QualityFinding],
    exceptions: dict[tuple[str, str, str | None], QualityException],
    metrics: list[QualityMetric],
    gate: GateResult,
) -> dict[str, Any]:
    rule_by_id = {rule.id: rule for rule in rules.values()}
    exception_rows = []
    for (rule_code, entity_type, mbid), exception in sorted(
        exceptions.items(),
        key=lambda item: (item[0][0], item[0][1], item[0][2] or ""),
    ):
        exception_rows.append(
            {
                "rule_code": rule_code,
                "entity_type": entity_type,
                "entity_mbid": mbid,
                "reason": exception.reason,
                "approved_by": exception.approved_by,
                "approved_at": exception.approved_at.isoformat(),
            }
        )
    finding_rows = [
        {
            "rule_code": rule_by_id[finding.rule_id].code,
            "entity_type": finding.entity_type,
            "entity_mbid": finding.entity_mbid,
            "entity_id": str(finding.entity_id) if finding.entity_id else None,
            "severity": finding.severity,
            "status": finding.status,
            "observed_value": finding.observed_value,
            "expected_value": finding.expected_value,
            "details": finding.details,
        }
        for finding in findings
    ]
    metric_rows = [
        {
            "metric_code": metric.metric_code,
            "dimension": metric.dimension,
            "scope_type": metric.scope_type,
            "scope_key": metric.scope_key,
            "numerator": metric.numerator,
            "denominator": metric.denominator,
            "value": metric.value,
            "unit": metric.unit,
            "missing_count": metric.missing_count,
            "details": metric.details,
        }
        for metric in metrics
    ]
    return {
        "run_id": str(run.id),
        "normalization_run_id": str(run.normalization_run_id),
        "status": run.status,
        "dataset_version": run.dataset_version,
        "taxonomy_version": run.taxonomy_version,
        "catalogue_version": run.catalogue_version,
        "code_version": run.code_version,
        "counters": run.counters,
        "gate": {
            "blocking_unexcepted": gate.blocking_unexcepted,
            "blocking_excepted": gate.blocking_excepted,
            "advisory": gate.advisory,
            "status": gate.status,
        },
        "findings": finding_rows,
        "exceptions": exception_rows,
        "metrics": metric_rows,
        "interpretation": INTERPRETATION,
    }


def _render(data: dict[str, Any]) -> str:
    lines = [
        "# HMDE data quality report",
        "",
        f"- Quality run: {data['run_id']}",
        f"- Normalization run: {data['normalization_run_id']}",
        f"- Status: {data['status']}",
        f"- Dataset: {data['dataset_version']}",
        f"- Taxonomy: {data['taxonomy_version']}",
        f"- Catalogue: {data['catalogue_version']}",
        f"- Code: {data['code_version']}",
        f"- Gate: {data['gate']['status']}",
        "",
        f"> {data['interpretation']}",
        "",
        "## Findings by severity",
        "",
    ]
    severities = Counter(finding["severity"] for finding in data["findings"])
    for severity in ("blocking", "high", "medium", "info"):
        lines.append(f"- {severity}: {severities.get(severity, 0)}")
    lines.extend(["", "## Findings", ""])
    if data["findings"]:
        lines.extend(
            [
                "| Rule | Entity | MBID | Severity | Status |",
                "|---|---|---|---|---|",
            ]
        )
        for finding in data["findings"]:
            lines.append(
                f"| {finding['rule_code']} | {finding['entity_type']} | "
                f"{finding['entity_mbid'] or ''} | {finding['severity']} | "
                f"{finding['status']} |"
            )
    else:
        lines.append("No findings.")
    lines.extend(["", "## Exceptions", ""])
    if data["exceptions"]:
        lines.extend(
            [
                "| Rule | Entity | MBID | Reason | Approved by |",
                "|---|---|---|---|---|",
            ]
        )
        for exception in data["exceptions"]:
            lines.append(
                f"| {exception['rule_code']} | {exception['entity_type']} | "
                f"{exception['entity_mbid'] or ''} | {exception['reason']} | "
                f"{exception['approved_by']} |"
            )
    else:
        lines.append("No exceptions.")
    lines.extend(["", "## Metrics", ""])
    if data["metrics"]:
        lines.extend(
            [
                "| Metric | Dimension | Scope | Value | Denominator | Missing |",
                "|---|---|---|---:|---:|---:|",
            ]
        )
        for metric in data["metrics"]:
            lines.append(
                f"| {metric['metric_code']} | {metric['dimension']} | "
                f"{metric['scope_type']}={metric['scope_key']} | "
                f"{metric['value']:.4f} | {metric['denominator']:.0f} | "
                f"{metric['missing_count'] if metric['missing_count'] is not None else ''} |"
            )
    else:
        lines.append("No metrics.")
    lines.extend(["", "## Gate", ""])
    lines.append(f"- Blocking unexcepted: {data['gate']['blocking_unexcepted']}")
    lines.append(f"- Blocking excepted: {data['gate']['blocking_excepted']}")
    lines.append(f"- Advisory: {data['gate']['advisory']}")
    return "\n".join(lines) + "\n"
