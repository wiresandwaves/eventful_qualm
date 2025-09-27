# libs/ports/perf.py
from typing import Protocol


class PerfPort(Protocol):
    def fps(self) -> float | None: ...
