from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ports.ipc import AgentCommandPort, TelemetryPubPort, TelemetrySubPort


class InprocAgentCommandPort(AgentCommandPort):
    """Records last command per addr and returns a canned ok-dict."""

    @classmethod
    def create(cls) -> InprocAgentCommandPort:
        return cls()

    def send(self, addr: str, cmd: Any) -> dict[str, Any]:
        return {"ok": True, "data": {"echo": getattr(cmd, "type", "UNKNOWN")}}


class InprocTelemetryPubPort(TelemetryPubPort):
    """Agent-side PUB counterpart for in-proc transport (noop stub)."""

    @classmethod
    def create(cls) -> InprocTelemetryPubPort:
        return cls()

    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        pass


class InprocTelemetrySubPort(TelemetrySubPort):
    """Local queue-based telemetry channel suitable for tests."""

    @classmethod
    def create(cls) -> InprocTelemetrySubPort:
        return cls()

    def subscribe(self, addr: str) -> None:
        pass

    def recv(self, timeout_ms: int = 100) -> dict | None:
        return None


class InprocCommandServerPort:
    @classmethod
    def create(cls) -> InprocCommandServerPort:
        return cls()

    def poll_once(self, handler: Callable[[dict], dict]) -> bool:
        # No actual queue in the in-proc stub—just say "no work"
        return False

    def close(self) -> None:
        pass
