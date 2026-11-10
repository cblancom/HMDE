"""Shared API dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hmde.db.session import get_db
from hmde.models import AnalysisRun

COMPLETED_STATUSES = ("completed", "completed_with_limitations")


def resolve_analysis_run(
    session: Session,
    analysis_run_id: uuid.UUID | None = None,
) -> AnalysisRun:
    if analysis_run_id is not None:
        run = session.get(AnalysisRun, analysis_run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Analysis run not found")
        if run.status not in COMPLETED_STATUSES:
            raise HTTPException(status_code=409, detail="Analysis run is not terminal")
        return run

    run = session.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.status.in_(COMPLETED_STATUSES))
        .order_by(
            func.coalesce(AnalysisRun.finished_at, AnalysisRun.started_at).desc(),
            AnalysisRun.started_at.desc(),
        )
        .limit(1)
    )
    if run is None:
        raise HTTPException(status_code=503, detail="No completed analysis run available")
    return run


def get_analysis_run(
    db: Annotated[Session, Depends(get_db)],
    analysis_run_id: Annotated[uuid.UUID | None, Query(alias="analysis_run")] = None,
) -> AnalysisRun:
    return resolve_analysis_run(db, analysis_run_id)
