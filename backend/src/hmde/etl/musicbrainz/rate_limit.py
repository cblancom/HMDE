"""Process-wide request rate limiting."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class RateLimiter:
    def __init__(
        self,
        min_interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if min_interval_seconds <= 0:
            raise ValueError("min_interval_seconds must be greater than zero")
        self._min_interval_seconds = min_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_started_at: float | None = None
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            if self._last_started_at is not None:
                delay = self._min_interval_seconds - (now - self._last_started_at)
                if delay > 0:
                    self._sleep(delay)
                    now = self._clock()
            self._last_started_at = now
