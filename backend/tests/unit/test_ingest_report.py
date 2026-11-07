from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hmde.etl.musicbrainz.report import (
    COVERAGE_FILE,
    REPORT_FILE,
    build_coverage,
    render_report,
    write_report,
)
from tests.support.extractions import BAND, sample_extraction

SOURCE_TIME = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def _coverage() -> dict:
    return build_coverage(
        [sample_extraction()],
        dataset_version="mb-test",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
        counters={"requests": 7, "cache_hits": 2, "retries": 0},
        failures=[
            {
                "band_mbid": BAND,
                "phase": "band",
                "error_type": "ExampleError",
                "message": "synthetic failure",
                "attempts": 1,
            }
        ],
    )


def test_build_coverage_summarizes_dataset() -> None:
    coverage = _coverage()

    assert coverage["summary"] == {
        "bands": 1,
        "bands_with_wikidata_qid": 1,
        "bands_with_producer": 1,
        "release_groups": 1,
        "albums_with_producer": 1,
        "releases": 1,
        "recordings": 2,
        "credits": 3,
        "places": 1,
        "exclusions": 1,
    }
    assert coverage["credits_by_scope"] == {
        "recording": 1,
        "release": 1,
        "release_group": 1,
    }
    assert coverage["credits_by_role"] == {"engineer": 1, "producer": 2}
    assert coverage["exclusions_by_reason"] == {"secondary_type": 1}
    assert coverage["subgenres"]["Heavy Metal"]["bands"] == 1
    assert coverage["subgenres"]["Heavy Metal"]["albums_with_producer"] == 1
    assert coverage["decades"]["1980s"]["release_groups"] == 1
    assert coverage["decades"]["1980s"]["albums_with_producer"] == 1
    assert coverage["run"]["counters"]["requests"] == 7
    assert coverage["run"]["failures"][0]["error_type"] == "ExampleError"
    assert "not negative evidence" in coverage["interpretation"]


def test_render_report_contains_required_sections_and_warning() -> None:
    markdown = render_report(_coverage())

    assert "# MusicBrainz ingestion coverage" in markdown
    assert "Credits by scope" in markdown
    assert "Credits by role" in markdown
    assert "Coverage by subgenre" in markdown
    assert "Coverage by decade" in markdown
    assert "Exclusions by reason" in markdown
    assert "Per-band coverage" in markdown
    assert "No recorded failures" not in markdown
    assert "Missing data is not negative evidence" in markdown
    assert "| Heavy Metal | 1 | 1 |" in markdown


def test_write_report_creates_json_and_markdown(tmp_path: Path) -> None:
    result = write_report(
        tmp_path,
        [sample_extraction()],
        dataset_version="mb-test",
        seed_list_version="0.1.0",
        source_snapshot_at=SOURCE_TIME,
        code_version="test-version",
        counters={"requests": 7},
    )

    assert result.coverage_path == tmp_path / COVERAGE_FILE
    assert result.report_path == tmp_path / REPORT_FILE
    assert result.coverage_path.is_file()
    assert "## Summary" in result.report_path.read_text(encoding="utf-8")
    assert '"bands": 1' in result.coverage_path.read_text(encoding="utf-8")
