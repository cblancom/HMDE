from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from hmde.models import AnalysisRun
from hmde.network.graph import build_producer_album_layer, build_producer_band_layer
from hmde.network.loader import AlbumRow, NetworkData, ProducerAlbumRoleRow, QualitySummary
from hmde.network.metrics import compute_metrics
from hmde.network.report import MANIFEST_JSON, REPORT_JSON, REPORT_MARKDOWN, write_network_report


def _run() -> AnalysisRun:
    return AnalysisRun(
        id=uuid.uuid4(),
        analysis_version="net-test",
        normalization_run_id=uuid.uuid4(),
        quality_run_id=uuid.uuid4(),
        dataset_version="mb-test",
        taxonomy_version="0.2.0",
        graph_version="0.1.0",
        code_version="test",
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        parameters={"top_k": 20},
        counters={"graphs": {}},
        report_path=None,
    )


def test_report_writes_json_markdown_and_manifest(tmp_path: Path) -> None:
    album = AlbumRow(
        album_id=uuid.uuid4(),
        album_mbid=str(uuid.uuid4()),
        album_title="Album",
        first_release_date=date(1991, 1, 1),
        band_id=uuid.uuid4(),
        band_name="Band",
        band_mbid=str(uuid.uuid4()),
        band_type="group",
        band_country="US",
        primary_code="heavy-metal",
        primary_status="approved",
    )
    producer = uuid.uuid4()
    row = ProducerAlbumRoleRow(
        producer_id=producer,
        producer_name="Producer",
        producer_mbid=str(uuid.uuid4()),
        producer_type="person",
        producer_country="GB",
        album_id=album.album_id,
        role_code="producer",
        supporting_recordings=1,
        album_recordings=1,
        support_ratio=1.0,
        has_release_group_scope=True,
        scope_mix={"release_group": 1},
        evidence={"credit_ids": [], "source_record_ids": []},
    )
    data = NetworkData(
        albums={album.album_id: album},
        producer_albums=(row,),
        quality=QualitySummary({}, 0, 0, 0, ()),
    )
    album_layer = build_producer_album_layer(data)
    band_layer = build_producer_band_layer(data, album_layer)
    metrics = compute_metrics(data, album_layer, band_layer)
    result = write_network_report(
        tmp_path,
        run=_run(),
        data=data,
        metrics=metrics,
    )
    assert result.report_path.is_file()
    assert result.markdown_path.is_file()
    assert result.manifest_path.is_file()
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["analysis_version"] == "net-test"
    assert payload["top_albums"][0]["producer"] == "Producer"
    assert "Producer–album" in result.markdown_path.read_text(encoding="utf-8")
    assert (
        json.loads(result.manifest_path.read_text(encoding="utf-8"))["analysis_version"]
        == "net-test"
    )
    assert {REPORT_JSON, REPORT_MARKDOWN, MANIFEST_JSON} <= {
        path.name for path in result.output_dir.iterdir()
    }
