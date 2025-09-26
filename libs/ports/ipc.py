from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable


class Command(Protocol):
    type: str  # "PING" | "HOLD" | ...


class AgentCommandPort(ABC):
    """Coordinator → Agent commands (REQ/REP client)."""

    @abstractmethod
    def send(self, addr: str, cmd: Command) -> dict: ...


class TelemetrySubPort(ABC):
    """Coordinator subscribes to agent telemetry (SUB)."""

    @abstractmethod
    def subscribe(self, addr: str) -> None: ...
    @abstractmethod
    def recv(self, timeout_ms: int = 100) -> dict | None: ...


class TelemetryPubPort(ABC):
    """Agent publishes telemetry (PUB)."""

    @abstractmethod
    def publish(self, topic: str, payload: Mapping[str, Any]) -> None: ...


@runtime_checkable
class CommandServerPort(Protocol):
    """Agent-side REP server: poll once and close."""

    def poll_once(self, handler: Callable[[dict], dict]) -> bool: ...
    def close(self) -> None: ...


__all__ = [
    "AgentCommandPort",
    "TelemetrySubPort",
    "TelemetryPubPort",
    "CommandServerPort",
    "Command",
]
