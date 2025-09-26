from __future__ import annotations

from queue import Empty, SimpleQueue
from typing import Any

from ports.ipc import AgentCommandPort, TelemetrySubPort


class FakeAgentCommandPort(AgentCommandPort):
    """Records last command per addr and returns a canned ok-dict."""

    def __init__(self) -> None:
        self.sent: dict[str, dict] = {}

    def send(self, addr: str, cmd: Any) -> dict:
        # Accept any mapping (e.g., Pydantic model .model_dump()).
        payload: dict[str, Any] = dict(cmd) if not isinstance(cmd, dict) else cmd
        self.sent[addr] = payload
        return {"ok": True, "echo": payload}


class FakeTelemetrySubPort(TelemetrySubPort):
    """Local queue-based telemetry channel suitable for tests."""

    def __init__(self) -> None:
        self._subs: set[str] = set()
        self._q: SimpleQueue[dict] = SimpleQueue()

    def subscribe(self, addr: str) -> None:
        self._subs.add(addr)

    def recv(self, timeout_ms: int = 100) -> dict | None:
        try:
            return self._q.get(timeout=timeout_ms / 1000.0)
        except Empty:
            return None

    # Test/helper API: inject a telemetry record
    def inject(self, record: dict) -> None:
        self._q.put(record)
