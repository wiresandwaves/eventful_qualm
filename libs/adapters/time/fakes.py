from __future__ import annotations

import time

from ports.time import ClockPort, SleeperPort


class FakeClockPort(ClockPort):
    """Wall-clock using perf_counter for monotonic timing."""

    def now(self) -> float:
        return time.perf_counter()


class FakeSleeperPort(SleeperPort):
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
