"""Network-layer errors."""

from __future__ import annotations


class NetworkError(ValueError):
    """Base error for network analysis execution."""


class NetworkInputError(NetworkError):
    """A network input or selected run is invalid."""
