"""Logging configuration for the HMDE backend."""

from __future__ import annotations

import logging
import sys


def resolve_log_level(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=resolve_log_level(level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
