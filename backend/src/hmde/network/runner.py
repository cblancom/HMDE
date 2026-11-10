"""End-to-end E7 orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from hmde.models import AnalysisRun

from . import GRAPH_VERSION
from .graph import build_producer_album_layer, build_producer_band_layer
from .inputs import NetworkInputs
from .loader import filter_network_data, load_network_data
from .metrics import compute_metrics
from .persistence import (
    analysis_version,
    find_completed_run,
    persist_network_run,
    start_analysis_run,
)
from .report import NetworkReportResult, write_network_report


@dataclass(frozen=True, slots=True)
class NetworkRunResult:
    run_id: uuid.UUID
    analysis_version: str
    status: str
    counters: dict[str, Any]
    report_path: Path | None
    markdown_path: Path | None
    advisory: bool
    reused: bool


def run_network(
    session: Session,
    inputs: NetworkInputs,
    *,
    code_version: str,
    output_dir: Path,
    top_k: int = 20,
    decade: str | None = None,
    subgenre: str | None = None,
    band_ids: tuple[uuid.UUID, ...] = (),
) -> NetworkRunResult:
    parameters = {
        "roles": ["producer", "co-producer"],
        "top_k": top_k,
        "decade": decade,
        "subgenre": subgenre,
        "bands": [str(band_id) for band_id in band_ids],
        "graph_version": GRAPH_VERSION,
    }
    version = analysis_version(
        inputs,
        graph_version=GRAPH_VERSION,
        code_version=code_version,
        parameters=parameters,
    )
    existing = find_completed_run(session, version=version)
    if existing is not None:
        return _result(existing, reused=True)

    data = filter_network_data(
        load_network_data(session, quality_run=inputs.quality_run),
        decade=decade,
        subgenre=subgenre,
        band_ids=band_ids,
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    metrics = compute_metrics(data, album_layer, band_layer, top_k=top_k)
    run = start_analysis_run(
        session,
        version=version,
        inputs=inputs,
        graph_version=GRAPH_VERSION,
        code_version=code_version,
        parameters=parameters,
    )
    persist_network_run(
        session,
        run=run,
        data=data,
        album_layer=album_layer,
        band_layer=band_layer,
        metrics=metrics,
    )
    report: NetworkReportResult = write_network_report(
        output_dir,
        run=run,
        data=data,
        metrics=metrics,
    )
    run.report_path = str(report.report_path)
    session.flush()
    return _result(run, reused=False, report=report)


def _result(
    run: AnalysisRun,
    *,
    reused: bool,
    report: NetworkReportResult | None = None,
) -> NetworkRunResult:
    report_path = report.report_path if report else _path_or_none(run.report_path)
    markdown_path = (
        report.markdown_path
        if report
        else (report_path.parent / "report.md" if report_path else None)
    )
    return NetworkRunResult(
        run_id=run.id,
        analysis_version=run.analysis_version,
        status=run.status,
        counters=dict(run.counters or {}),
        report_path=report_path,
        markdown_path=markdown_path,
        advisory=run.status == "completed_with_limitations",
        reused=reused,
    )


def _path_or_none(value: str | None) -> Path | None:
    return Path(value) if value else None
