"""Operational health endpoint."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from hmde.api.schemas.health import HealthResponse
from hmde.db.session import check_database, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
)
def health(db: Annotated[Session, Depends(get_db)]) -> HealthResponse | JSONResponse:
    try:
        check_database(db)
    except SQLAlchemyError:
        logger.warning("Database health check failed")
        return JSONResponse(
            status_code=503,
            content=HealthResponse(status="degraded", database="unavailable").model_dump(),
        )

    return HealthResponse(status="ok", database="ok")
