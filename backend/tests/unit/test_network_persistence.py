from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from hmde.models import NormalizationRun, QualityRun
from hmde.network.inputs import NetworkInputs
from hmde.network.persistence import analysis_version


def test_analysis_version_is_deterministic_and_parameter_sensitive() -> None:
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
    quality = QualityRun(
        id=uuid.uuid4(),
        normalization_run_id=normalization.id,
        dataset_version="mb-test",
        taxonomy_version="0.2.0",
        catalogue_version="0.1.0",
        code_version="test",
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        parameters={},
        counters={},
    )
    inputs = NetworkInputs(
        normalization_run=normalization,
        quality_run=quality,
        taxonomy_path=Path("data/taxonomy.json"),
        taxonomy_version="0.2.0",
    )
    first = analysis_version(
        inputs,
        graph_version="0.1.0",
        code_version="test",
        parameters={"top_k": 20},
    )
    second = analysis_version(
        inputs,
        graph_version="0.1.0",
        code_version="test",
        parameters={"top_k": 20},
    )
    third = analysis_version(
        inputs,
        graph_version="0.1.0",
        code_version="test",
        parameters={"top_k": 10},
    )
    assert first == second
    assert first != third
    assert first.startswith("net-")
