from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


class Command(Protocol):
    type: str  # e.g., "PING" | "HOLD" | "RESUME" | ...


class AgentCommandPort(ABC):
    """Coordinator → Agent commands."""

    @abstractmethod
    def send(self, addr: str, cmd: Command) -> dict: ...


class TelemetrySubPort(ABC):
    """Coordinator subscribes to agent telemetry."""

    @abstractmethod
    def subscribe(self, addr: str) -> None: ...

    @abstractmethod
    def recv(self, timeout_ms: int = 100) -> dict | None: ...
