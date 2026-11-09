"""Quality-layer errors."""

from __future__ import annotations


class QualityError(ValueError):
    """Base error for quality execution."""


class QualityInputError(QualityError):
    """A quality input or selected run is invalid."""


class QualityCatalogueError(QualityError):
    """The quality rule catalogue is malformed or inconsistent."""
