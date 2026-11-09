"""JSON/Markdown E6 reports and manifest."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalogue import MetricCatalogue
from .inputs import AnalysisInputs
from .metrics import AnalysisMetric

REPORT_JSON = "report.json"
REPORT_MARKDOWN = "report.md"
MANIFEST_JSON = "manifest.json"
INTERPRETATION = (
    "Missing data is not negative evidence. Results describe the available sample "
    "and its documented coverage, not the complete heavy metal scene."
)


@dataclass(frozen=True, slots=True)
class AnalysisReportResult:
    analysis_version: str
    output_dir: Path
    report_path: Path
    markdown_path: Path
    data: dict[str, Any]


def analysis_version(
    inputs: AnalysisInputs,
    *,
    code_version: str,
) -> str:
    context = {
        "dataset_version": inputs.normalization_run.dataset_version,
        "normalization_run_id": str(inputs.normalization_run.id),
        "taxonomy_version": inputs.normalization_run.taxonomy_version,
        "quality_run_id": str(inputs.quality_run.id),
        "catalogue_version": inputs.catalogue.version,
        "catalogue_hash": inputs.catalogue.source_hash,
        "code_version": code_version,
    }
    digest = hashlib.sha256(
        json.dumps(context, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"eda-{digest[:16]}"


def write_report(
    output_root: Path,
    *,
    inputs: AnalysisInputs,
    metrics: list[AnalysisMetric],
    code_version: str,
) -> AnalysisReportResult:
    version = analysis_version(inputs, code_version=code_version)
    target = output_root / version
    fingerprint = _fingerprint(inputs, code_version)
    if target.exists():
        manifest = json.loads((target / MANIFEST_JSON).read_text(encoding="utf-8"))
        if manifest.get("input_fingerprint") == fingerprint:
            return AnalysisReportResult(
                analysis_version=version,
                output_dir=target,
                report_path=target / REPORT_JSON,
                markdown_path=target / REPORT_MARKDOWN,
                data=json.loads((target / REPORT_JSON).read_text(encoding="utf-8")),
            )
        raise FileExistsError(f"analysis version already exists with different inputs: {target}")
    target.mkdir(parents=True)
    data = _report_data(inputs, metrics, version, code_version)
    report_path = target / REPORT_JSON
    markdown_path = target / REPORT_MARKDOWN
    report_path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render(data, inputs.catalogue), encoding="utf-8")
    files = {
        name: hashlib.sha256((target / name).read_bytes()).hexdigest()
        for name in (REPORT_JSON, REPORT_MARKDOWN)
    }
    manifest = {
        "analysis_version": version,
        "input_fingerprint": fingerprint,
        "generated_at": data["generated_at"],
        "files": files,
        "metric_count": len(metrics),
    }
    (target / MANIFEST_JSON).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return AnalysisReportResult(
        analysis_version=version,
        output_dir=target,
        report_path=report_path,
        markdown_path=markdown_path,
        data=data,
    )


def _report_data(
    inputs: AnalysisInputs,
    metrics: list[AnalysisMetric],
    version: str,
    code_version: str,
) -> dict[str, Any]:
    return {
        "analysis_version": version,
        "generated_at": datetime.now(UTC).isoformat(),
        "code_version": code_version,
        "dataset_version": inputs.normalization_run.dataset_version,
        "normalization_run_id": str(inputs.normalization_run.id),
        "quality_run_id": str(inputs.quality_run.id),
        "taxonomy_version": inputs.normalization_run.taxonomy_version,
        "catalogue_version": inputs.catalogue.version,
        "catalogue_hash": inputs.catalogue.source_hash,
        "metrics": [asdict(metric) for metric in metrics],
        "interpretation": INTERPRETATION,
    }


def _fingerprint(inputs: AnalysisInputs, code_version: str) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "dataset_version": inputs.normalization_run.dataset_version,
                "normalization_run_id": str(inputs.normalization_run.id),
                "taxonomy_version": inputs.normalization_run.taxonomy_version,
                "quality_run_id": str(inputs.quality_run.id),
                "catalogue_hash": inputs.catalogue.source_hash,
                "code_version": code_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _render(data: dict[str, Any], catalogue: MetricCatalogue) -> str:
    definitions = catalogue.by_code()
    lines = [
        "# HMDE exploratory analysis",
        "",
        f"- Analysis version: {data['analysis_version']}",
        f"- Dataset: {data['dataset_version']}",
        f"- Normalization run: {data['normalization_run_id']}",
        f"- Quality run: {data['quality_run_id']}",
        f"- Taxonomy: {data['taxonomy_version']}",
        f"- Metric catalogue: {data['catalogue_version']}",
        "",
        f"> {data['interpretation']}",
        "",
        "## Metrics",
        "",
        "| Code | Scope | Numerator | Denominator | Value |",
        "|---|---|---:|---:|---:|",
    ]
    for metric in data["metrics"]:
        lines.append(
            f"| {metric['metric_code']} | {metric['scope_type']}={metric['scope_key']} | "
            f"{metric['numerator']:.0f} | {metric['denominator']:.0f} | "
            f"{metric['value']:.4f} |"
        )
    lines.extend(["", "## Metric definitions", ""])
    for code in sorted({metric["metric_code"] for metric in data["metrics"]}):
        definition = definitions.get(code)
        if definition:
            lines.append(f"### {code} — {definition.name}")
            lines.append("")
            lines.append(definition.interpretation)
            lines.append("")
            lines.append(f"Limitations: {definition.limitations}")
            lines.append("")
    lines.extend(["## Interpretation limits", "", INTERPRETATION, ""])
    return "\n".join(lines)
