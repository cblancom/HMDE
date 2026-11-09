"""Analytics errors."""

from __future__ import annotations


class AnalysisError(ValueError):
    """Base error for E6 analysis."""


class AnalysisInputError(AnalysisError):
    """An analysis input or version is invalid."""


class MetricCatalogueError(AnalysisError):
    """The metric catalogue is malformed."""
