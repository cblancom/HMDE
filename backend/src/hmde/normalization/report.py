"""Normalization reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hmde.models import NormalizationIssue, NormalizationRun

from .aggregates import AggregateResult
from .classification import ClassificationResult
from .credits import CreditNormalizationResult
from .entities import EntityIndex
from .issues import serialize_issue
from .membership import MembershipCounts

REPORT_JSON = "report.json"
REPORT_MARKDOWN = "report.md"
INTERPRETATION = (
    "Missing data is not negative evidence: absence of a tag, mapping, credit, "
    "date or identifier means the source did not provide it in this dataset snapshot."
)


@dataclass(frozen=True, slots=True)
class ReportResult:
    json_path: Path
    markdown_path: Path
    data: dict[str, Any]


def write_normalization_report(
    output_dir: Path,
    *,
    run: NormalizationRun,
    dataset_version: str,
    taxonomy_version: str,
    tag_map_version: str,
    overrides_version: str,
    index: EntityIndex,
    credits: CreditNormalizationResult,
    classification: ClassificationResult,
    aggregates: AggregateResult,
    membership: MembershipCounts | None,
    issues: list[NormalizationIssue],
) -> ReportResult:
    target = output_dir / str(run.id)
    target.mkdir(parents=True, exist_ok=True)
    data = build_report(
        run=run,
        dataset_version=dataset_version,
        taxonomy_version=taxonomy_version,
        tag_map_version=tag_map_version,
        overrides_version=overrides_version,
        index=index,
        credits=credits,
        classification=classification,
        aggregates=aggregates,
        membership=membership,
        issues=issues,
    )
    json_path = target / REPORT_JSON
    markdown_path = target / REPORT_MARKDOWN
    json_path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_report(data), encoding="utf-8")
    return ReportResult(json_path=json_path, markdown_path=markdown_path, data=data)


def build_report(
    *,
    run: NormalizationRun,
    dataset_version: str,
    taxonomy_version: str,
    tag_map_version: str,
    overrides_version: str,
    index: EntityIndex,
    credits: CreditNormalizationResult,
    classification: ClassificationResult,
    aggregates: AggregateResult,
    membership: MembershipCounts | None,
    issues: list[NormalizationIssue],
) -> dict[str, Any]:
    return {
        "run_id": str(run.id),
        "status": run.status,
        "dataset_version": dataset_version,
        "taxonomy_version": taxonomy_version,
        "tag_map_version": tag_map_version,
        "overrides_version": overrides_version,
        "counts": {
            "entities": asdict(index.counts),
            "credits": asdict(credits.counts),
            "classification": asdict(classification.counts),
            "aggregates": asdict(aggregates.counts),
            "membership": asdict(membership) if membership is not None else None,
            "issues": len(issues),
        },
        "issues": [serialize_issue(issue) for issue in issues],
        "quarantined_credits": [
            {
                "source_key": item.source_key,
                "reason": item.reason,
                "record": item.record,
            }
            for item in credits.quarantined
        ],
        "interpretation": INTERPRETATION,
    }


def render_report(data: dict[str, Any]) -> str:
    lines = [
        "# HMDE normalization report",
        "",
        f"- Run: {data['run_id']}",
        f"- Status: {data['status']}",
        f"- Dataset: {data['dataset_version']}",
        f"- Taxonomy: {data['taxonomy_version']}",
        f"- Tag map: {data['tag_map_version']}",
        f"- Overrides: {data['overrides_version']}",
        "",
        f"> {data['interpretation']}",
        "",
        "## Counts",
        "",
    ]
    for group, values in data["counts"].items():
        if not isinstance(values, dict):
            lines.append(f"- {group}: {values}")
            continue
        lines.append(f"### {group}")
        lines.append("")
        for key, value in values.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.extend(["## Issues", ""])
    if data["issues"]:
        lines.extend(
            [
                "| Entity | MBID | Type | Severity | Status | Reason |",
                "|---|---|---|---|---|---|",
            ]
        )
        for issue in data["issues"]:
            lines.append(
                f"| {issue['entity_type']} | {issue['entity_mbid'] or ''} | "
                f"{issue['issue_type']} | {issue['severity']} | "
                f"{issue['status']} | {issue['reason']} |"
            )
    else:
        lines.append("No open issues.")
    lines.extend(["", "## Quarantined credits", ""])
    if data["quarantined_credits"]:
        for item in data["quarantined_credits"]:
            lines.append(f"- {item['source_key']}: {item['reason']}")
    else:
        lines.append("No quarantined credits.")
    return "\n".join(lines) + "\n"
