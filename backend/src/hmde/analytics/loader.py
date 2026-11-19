"""Read-only Pandas data loading for E6."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from hmde.models import NormalizationRun, QualityRun

from .errors import AnalysisInputError

BANDS_SQL = text(
    """
    SELECT a.id, a.mbid, a.name, a.country,
           ag.subgenre_code AS aggregate_code,
           ag.status AS aggregate_status,
           (
             SELECT e.external_id FROM external_id e
             WHERE e.entity_type = 'artist' AND e.entity_id = a.id
               AND e.source = 'wikidata'
             ORDER BY e.external_id LIMIT 1
           ) AS qid
    FROM artist a
    JOIN artist_subgenre ag
      ON ag.artist_id = a.id
     AND ag.is_primary
    JOIN dataset_membership dm
      ON dm.artist_id = a.id
     AND dm.dataset_version = :dataset_version
     AND dm.lifecycle = 'active'
    """
)
ALBUMS_SQL = text(
    """
    SELECT rg.id, rg.mbid, rg.title, rg.first_release_date,
           rg.first_release_precision,
           a.id AS artist_id, a.name AS artist_name, a.country AS artist_country,
           rgs.subgenre_code AS primary_code,
           rgs.status AS primary_status
    FROM release_group rg
    JOIN artist a ON a.id = rg.artist_id
    JOIN dataset_membership dm
      ON dm.artist_id = a.id
     AND dm.dataset_version = :dataset_version
     AND dm.lifecycle = 'active'
    LEFT JOIN release_group_subgenre rgs
      ON rgs.release_group_id = rg.id
     AND rgs.taxonomy_version = :taxonomy_version
     AND rgs.is_primary
    """
)
SECONDARY_SQL = text(
    """
    SELECT rgs.release_group_id, rgs.subgenre_code, rgs.status
    FROM release_group_subgenre rgs
    JOIN release_group rg ON rg.id = rgs.release_group_id
    JOIN artist a ON a.id = rg.artist_id
    JOIN dataset_membership dm
      ON dm.artist_id = a.id
     AND dm.dataset_version = :dataset_version
     AND dm.lifecycle = 'active'
    WHERE rgs.taxonomy_version = :taxonomy_version AND NOT rgs.is_primary
    """
)
CREDITS_SQL = text(
    """
    SELECT c.id, c.artist_id, ca.name AS artist_name, c.role_code, c.scope,
           c.release_group_id, rg.title AS album_title,
           rg.first_release_date,
           ba.id AS band_id, ba.name AS band_name
    FROM credit c
    JOIN artist ca ON ca.id = c.artist_id
    JOIN release_group rg ON rg.id = c.release_group_id
    JOIN artist ba ON ba.id = rg.artist_id
    JOIN dataset_membership dm
      ON dm.artist_id = ba.id
     AND dm.dataset_version = :dataset_version
     AND dm.lifecycle = 'active'
    """
)
MEMBERSHIP_SQL = text(
    """
    SELECT batch_id, lifecycle, count(*) AS count
    FROM dataset_membership
    WHERE dataset_version = :dataset_version
    GROUP BY batch_id, lifecycle
    ORDER BY batch_id, lifecycle
    """
)
RELEASES_SQL = text(
    """
    SELECT count(DISTINCT r.id) AS count
    FROM release r
    JOIN release_group rg ON rg.id = r.release_group_id
    JOIN artist a ON a.id = rg.artist_id
    JOIN dataset_membership dm
      ON dm.artist_id = a.id
     AND dm.dataset_version = :dataset_version
     AND dm.lifecycle = 'active'
    """
)
RECORDINGS_SQL = text(
    """
    SELECT count(DISTINCT rec.id) AS count
    FROM recording rec
    JOIN recording_release rr ON rr.recording_id = rec.id
    JOIN release r ON r.id = rr.release_id
    JOIN release_group rg ON rg.id = r.release_group_id
    JOIN artist a ON a.id = rg.artist_id
    JOIN dataset_membership dm
      ON dm.artist_id = a.id
     AND dm.dataset_version = :dataset_version
     AND dm.lifecycle = 'active'
    """
)
SOURCE_SQL = text(
    """
    SELECT source, count(*) AS count
    FROM source_record
    WHERE dataset_version = :dataset_version
    GROUP BY source
    ORDER BY source
    """
)
QUALITY_SQL = text(
    """
    SELECT qr.code AS rule_code, qf.severity, qf.status, count(*) AS count
    FROM quality_finding qf
    JOIN quality_rule qr ON qr.id = qf.rule_id
    WHERE qf.quality_run_id = :quality_run_id
    GROUP BY qr.code, qf.severity, qf.status
    ORDER BY qr.code, qf.severity, qf.status
    """
)
EXCEPTIONS_SQL = text(
    """
    SELECT count(*) AS count
    FROM quality_exception
    WHERE catalogue_version = :catalogue_version AND status = 'active'
    """
)


@dataclass(frozen=True, slots=True)
class AnalysisFrames:
    bands: pd.DataFrame
    albums: pd.DataFrame
    secondary_labels: pd.DataFrame
    credits: pd.DataFrame
    membership: pd.DataFrame
    sources: pd.DataFrame
    quality: pd.DataFrame
    taxonomy: pd.DataFrame
    active_exceptions: int
    entity_counts: dict[str, int]


def load_frames(
    session: Session,
    *,
    normalization_run: NormalizationRun,
    quality_run: QualityRun,
    taxonomy_path: Path,
) -> AnalysisFrames:
    taxonomy = _taxonomy(taxonomy_path)
    taxonomy_version = normalization_run.taxonomy_version or ""
    dataset_version = normalization_run.dataset_version or ""
    connection = session.connection()
    params = {
        "dataset_version": dataset_version,
        "taxonomy_version": taxonomy_version,
    }
    bands = pd.read_sql(BANDS_SQL, connection, params=params)
    albums = pd.read_sql(ALBUMS_SQL, connection, params=params)
    secondary = pd.read_sql(SECONDARY_SQL, connection, params=params)
    credits = pd.read_sql(CREDITS_SQL, connection, params=params)
    membership = pd.read_sql(MEMBERSHIP_SQL, connection, params=params)
    sources = pd.read_sql(
        SOURCE_SQL,
        connection,
        params={"dataset_version": dataset_version},
    )
    quality = pd.read_sql(
        QUALITY_SQL,
        connection,
        params={"quality_run_id": quality_run.id},
    )
    active_exceptions = int(
        pd.read_sql(
            EXCEPTIONS_SQL,
            connection,
            params={"catalogue_version": quality_run.catalogue_version},
        ).iloc[0]["count"]
    )
    releases = int(pd.read_sql(RELEASES_SQL, connection, params=params).iloc[0]["count"])
    recordings = int(pd.read_sql(RECORDINGS_SQL, connection, params=params).iloc[0]["count"])
    counts = {
        "bands": len(bands),
        "albums": len(albums),
        "releases": releases,
        "recordings": recordings,
        "credits": len(credits),
        "membership": int(membership["count"].sum()) if not membership.empty else 0,
        "source_records": int(sources["count"].sum()) if not sources.empty else 0,
    }
    return AnalysisFrames(
        bands=bands,
        albums=albums,
        secondary_labels=secondary,
        credits=credits,
        membership=membership,
        sources=sources,
        quality=quality,
        taxonomy=taxonomy,
        active_exceptions=active_exceptions,
        entity_counts=counts,
    )


def _taxonomy(path: Path) -> pd.DataFrame:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisInputError(f"could not read taxonomy: {path}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
        raise AnalysisInputError("taxonomy must contain nodes")
    frame = pd.DataFrame(payload["nodes"])
    required = {"code", "name", "parent_code", "assignable"}
    if not required <= set(frame.columns):
        raise AnalysisInputError("taxonomy nodes are missing required fields")
    return frame
