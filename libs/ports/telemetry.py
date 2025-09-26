from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal, Protocol

# Keep this in ports so it’s shared (no domain dependency)
AgentState = Literal["ACTIVE", "ASSIST", "HOLD"]


class TelemetryRecord(Protocol):
    agent_id: str
    state: AgentState
    ts: float


class TelemetryPort(ABC):
    @abstractmethod
    def publish(self, record: TelemetryRecord) -> None: ...


class MetricsPort(ABC):
    @abstractmethod
    def observe(self, name: str, value: float, **labels: str) -> None: ...
