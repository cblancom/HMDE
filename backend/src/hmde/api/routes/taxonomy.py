"""Taxonomy API route."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from hmde.db.session import get_db
from hmde.schemas.api import TaxonomyResponse
from hmde.services.taxonomy import get_taxonomy

router = APIRouter(prefix="/api/v1/taxonomy", tags=["taxonomy"])


@router.get("", response_model=TaxonomyResponse)
def taxonomy_endpoint(
    db: Annotated[Session, Depends(get_db)],
    version: Annotated[str | None, Query(max_length=50)] = None,
) -> TaxonomyResponse:
    taxonomy = get_taxonomy(db, version)
    if taxonomy is None:
        raise HTTPException(status_code=404, detail="Taxonomy not found")
    return taxonomy
