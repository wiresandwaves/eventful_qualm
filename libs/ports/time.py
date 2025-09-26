from __future__ import annotations

from abc import ABC, abstractmethod


class ClockPort(ABC):
    @abstractmethod
    def now(self) -> float: ...


class SleeperPort(ABC):
    @abstractmethod
    def sleep(self, seconds: float) -> None: ...
