from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

from hmde.analytics.catalogue import load_metric_catalogue
from hmde.analytics.report import write_report

DATA = Path(__file__).resolve().parents[3] / "data"
CATALOGUE = DATA / "metrics" / "catalogue-v0.1.0.json"


def _inputs(dataset_version: str):
    return SimpleNamespace(
        normalization_run=SimpleNamespace(
            id=uuid.uuid4(),
            dataset_version=dataset_version,
            taxonomy_version="0.2.0",
        ),
        quality_run=SimpleNamespace(id=uuid.uuid4()),
        catalogue=load_metric_catalogue(CATALOGUE),
        taxonomy_path=DATA / "taxonomy.json",
    )


def test_corpus_expansion_creates_new_analysis_version(tmp_path: Path) -> None:
    first = write_report(
        tmp_path,
        inputs=_inputs("mb-v0.2"),
        metrics=[],
        code_version="test",
    )
    first_report = first.report_path.read_bytes()
    second = write_report(
        tmp_path,
        inputs=_inputs("mb-v0.3"),
        metrics=[],
        code_version="test",
    )

    assert first.analysis_version != second.analysis_version
    assert first.report_path.read_bytes() == first_report
    assert first.output_dir != second.output_dir
