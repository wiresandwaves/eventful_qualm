from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ports.ipc import AgentCommandPort, TelemetryPubPort, TelemetrySubPort


class ZmqAgentCommandPort(AgentCommandPort):
    def __init__(self) -> None:
        pass

    @classmethod
    def bind_rep(cls, addr: str) -> ZmqAgentCommandPort:
        return cls()

    def send(self, addr: str, cmd) -> dict[str, Any]:
        raise NotImplementedError


class ZmqTelemetrySubPort(TelemetrySubPort):
    def __init__(self) -> None:
        pass

    def subscribe(self, addr: str) -> None:
        raise NotImplementedError

    def recv(self, timeout_ms: int = 100):
        raise NotImplementedError


class ZmqTelemetryPubPort(TelemetryPubPort):
    @classmethod
    def bind_pub(cls, addr: str) -> ZmqTelemetryPubPort:
        return cls()

    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        raise NotImplementedError
