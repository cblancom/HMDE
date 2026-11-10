"""Shared list pagination helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import HTTPException, Query


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


def validate_sort(sort: str | None, allowed: set[str], default: str) -> str:
    if sort is None:
        return default
    if sort not in allowed:
        raise HTTPException(status_code=422, detail=f"Unsupported sort field: {sort}")
    return sort
