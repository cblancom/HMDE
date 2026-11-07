from __future__ import annotations

import pytest

from hmde.etl.musicbrainz.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_rate_limiter_enforces_minimum_interval() -> None:
    fake = FakeClock()
    limiter = RateLimiter(1.0, clock=fake.clock, sleep=fake.sleep)

    limiter.wait()
    limiter.wait()
    limiter.wait()

    assert fake.sleeps == [1.0, 1.0]


def test_rate_limiter_does_not_sleep_when_time_has_elapsed() -> None:
    fake = FakeClock()
    limiter = RateLimiter(1.0, clock=fake.clock, sleep=fake.sleep)

    limiter.wait()
    fake.now += 2.0
    limiter.wait()

    assert fake.sleeps == []


def test_rate_limiter_rejects_non_positive_interval() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        RateLimiter(0)
