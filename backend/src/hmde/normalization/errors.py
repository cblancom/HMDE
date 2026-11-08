"""Normalization errors."""

from __future__ import annotations


class NormalizationError(ValueError):
    """The normalization input or execution is invalid."""


class InputValidationError(NormalizationError):
    """An input dataset or classification file is invalid."""


class TaxonomyValidationError(NormalizationError):
    """The taxonomy is malformed or inconsistent."""


class ProvenanceError(NormalizationError):
    """A required source record or raw response is missing."""
