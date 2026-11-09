"""E6 analysis orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from .inputs import AnalysisInputs
from .loader import load_frames
from .metrics import all_metrics
from .report import AnalysisReportResult, write_report


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    analysis_version: str
    report_path: Path
    markdown_path: Path
    metric_count: int
    advisory: bool


def run_analysis(
    session: Session,
    inputs: AnalysisInputs,
    *,
    code_version: str,
    output_dir: Path,
) -> AnalysisResult:
    frames = load_frames(
        session,
        normalization_run=inputs.normalization_run,
        quality_run=inputs.quality_run,
        taxonomy_path=inputs.taxonomy_path,
    )
    metrics = all_metrics(frames)
    report: AnalysisReportResult = write_report(
        output_dir,
        inputs=inputs,
        metrics=metrics,
        code_version=code_version,
    )
    advisory = any(
        metric.metric_code == "EDA-LIM-001" and metric.numerator > 0 for metric in metrics
    )
    return AnalysisResult(
        analysis_version=report.analysis_version,
        report_path=report.report_path,
        markdown_path=report.markdown_path,
        metric_count=len(metrics),
        advisory=advisory,
    )
