"""JSON/Markdown reports for E7 network runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hmde.models import AnalysisRun

from .loader import NetworkData
from .metrics import MetricsPayload

REPORT_JSON = "report.json"
REPORT_MARKDOWN = "report.md"
MANIFEST_JSON = "manifest.json"
INTERPRETATION = (
    "Missing credits are not negative evidence. Producer–album and producer–band "
    "results describe the documented sample and its coverage, not the complete scene. "
    "Shared credits do not demonstrate affinity, influence or listener preference."
)


@dataclass(frozen=True, slots=True)
class NetworkReportResult:
    output_dir: Path
    report_path: Path
    markdown_path: Path
    manifest_path: Path
    data: dict[str, Any]


def write_network_report(
    output_root: Path,
    *,
    run: AnalysisRun,
    data: NetworkData,
    metrics: MetricsPayload,
) -> NetworkReportResult:
    target = output_root / run.analysis_version
    target.mkdir(parents=True, exist_ok=True)
    report = _report_data(run=run, data=data, metrics=metrics)
    report_path = target / REPORT_JSON
    markdown_path = target / REPORT_MARKDOWN
    manifest_path = target / MANIFEST_JSON
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render(report), encoding="utf-8")
    manifest = {
        "analysis_version": run.analysis_version,
        "run_id": str(run.id),
        "generated_at": report["generated_at"],
        "files": {
            name: hashlib.sha256((target / name).read_bytes()).hexdigest()
            for name in (REPORT_JSON, REPORT_MARKDOWN)
        },
        "counters": run.counters,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return NetworkReportResult(
        output_dir=target,
        report_path=report_path,
        markdown_path=markdown_path,
        manifest_path=manifest_path,
        data=report,
    )


def _report_data(
    *,
    run: AnalysisRun,
    data: NetworkData,
    metrics: MetricsPayload,
) -> dict[str, Any]:
    return {
        "analysis_version": run.analysis_version,
        "run_id": str(run.id),
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_version": run.dataset_version,
        "normalization_run_id": str(run.normalization_run_id),
        "quality_run_id": str(run.quality_run_id),
        "taxonomy_version": run.taxonomy_version,
        "graph_version": run.graph_version,
        "code_version": run.code_version,
        "parameters": run.parameters,
        "counters": run.counters,
        "graph_counts": metrics.graph_counts,
        "support": metrics.support_summary,
        "top_albums": list(metrics.top_albums),
        "top_bands": list(metrics.top_bands),
        "communities": [asdict(community) for community in metrics.communities],
        "temporal_metrics": [asdict(metric) for metric in metrics.temporal_metrics],
        "quality": asdict(data.quality),
        "advisories": list(metrics.advisories),
        "interpretation": INTERPRETATION,
    }


def _render(data: dict[str, Any]) -> str:
    lines = [
        "# HMDE producer network analysis",
        "",
        f"- Analysis version: {data['analysis_version']}",
        f"- Run: {data['run_id']}",
        f"- Dataset: {data['dataset_version']}",
        f"- Normalization run: {data['normalization_run_id']}",
        f"- Quality run: {data['quality_run_id']}",
        f"- Taxonomy: {data['taxonomy_version']}",
        f"- Graph version: {data['graph_version']}",
        f"- Code version: {data['code_version']}",
        "",
        f"> {data['interpretation']}",
        "",
        "## Graph counts",
        "",
        "| Layer | Nodes | Edges | Components |",
        "|---|---:|---:|---:|",
    ]
    for layer, counts in data["graph_counts"].items():
        lines.append(
            f"| {layer} | {counts['nodes']} | {counts['edges']} | {counts['components']} |"
        )
    support = data["support"]
    lines.extend(
        [
            "",
            "## Support",
            "",
            f"- Full: {support['full']}",
            f"- Partial: {support['partial']}",
            f"- Unknown: {support['unknown']}",
            "",
            "## Top producers by albums",
            "",
            "| Producer | Albums | Share |",
            "|---|---:|---:|",
        ]
    )
    for row in data["top_albums"]:
        lines.append(f"| {row['producer']} | {row['count']} | {row['share']:.4f} |")
    lines.extend(
        [
            "",
            "## Top producers by bands/artists",
            "",
            "| Producer | Bands/artists | Share |",
            "|---|---:|---:|",
        ]
    )
    for row in data["top_bands"]:
        lines.append(f"| {row['producer']} | {row['count']} | {row['share']:.4f} |")
    lines.extend(["", "## Communities", ""])
    if data["communities"]:
        lines.extend(["| Community | Algorithm | Size |", "|---|---|---:|"])
        for community in data["communities"]:
            lines.append(
                f"| {community['community_key']} | {community['algorithm']} | {community['size']} |"
            )
    else:
        lines.append("No communities.")
    lines.extend(["", "## Temporal metrics", ""])
    if data["temporal_metrics"]:
        lines.extend(["| Layer | Scope | Metric | Value |", "|---|---|---|---:|"])
        for metric in data["temporal_metrics"]:
            lines.append(
                f"| {metric['layer_code']} | {metric['scope_type']}:{metric['scope_key']} | "
                f"{metric['metric_code']} | {metric['value']:.4f} |"
            )
    else:
        lines.append("No temporal metrics.")
    quality = data["quality"]
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            f"- Active quality exceptions: {quality['active_exceptions']}",
            f"- Missing album dates: {quality['missing_dates']}",
            f"- Unclassified albums: {quality['unclassified_albums']}",
            f"- Possible duplicate labels with different MBIDs: {len(quality['duplicate_labels'])}",
        ]
    )
    for advisory in data["advisories"]:
        lines.append(f"- {advisory}")
    lines.extend(["", "## Interpretation limits", "", INTERPRETATION, ""])
    return "\n".join(lines)
