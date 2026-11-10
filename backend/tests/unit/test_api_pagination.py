from __future__ import annotations

import pytest
from fastapi import HTTPException

from hmde.api.pagination import validate_sort


def test_validate_sort_returns_default_and_allowed() -> None:
    assert validate_sort(None, {"name", "album_count"}, "name") == "name"
    assert validate_sort("album_count", {"name", "album_count"}, "name") == "album_count"


def test_validate_sort_rejects_unknown_field() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_sort("drop_table", {"name"}, "name")
    assert exc.value.status_code == 422
