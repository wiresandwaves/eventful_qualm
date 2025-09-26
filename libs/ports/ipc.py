from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, Protocol


class Command(Protocol):
    type: str  # e.g., "PING" | "HOLD" | "RESUME" | ...


class AgentCommandPort(ABC):
    """Coordinator → Agent commands (REQ/REP)."""

    @abstractmethod
    def send(self, addr: str, cmd: Command) -> dict: ...


class TelemetrySubPort(ABC):
    """Coordinator subscribes to agent telemetry (SUB)."""

    @abstractmethod
    def subscribe(self, addr: str) -> None: ...

    @abstractmethod
    def recv(self, timeout_ms: int = 100) -> dict | None: ...


class TelemetryPubPort(ABC):
    """Agent publishes telemetry (PUB).

    Note: composition is responsible for binding/connect configuration.
    This interface only covers the act of publishing a message.
    """

    @abstractmethod
    def publish(self, topic: str, payload: Mapping[str, Any]) -> None: ...
