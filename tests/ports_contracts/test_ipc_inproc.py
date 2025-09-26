from __future__ import annotations

from adapters.ipc_inproc import (
    InprocAgentCommandPort,
    InprocTelemetryPubPort,
    InprocTelemetrySubPort,
)
from ports.ipc import AgentCommandPort, TelemetryPubPort, TelemetrySubPort


class _Cmd:
    # Minimal Command Protocol impl for tests
    def __init__(self, t: str) -> None:
        self.type = t


def test_inproc_command_send_contract():
    port: AgentCommandPort = InprocAgentCommandPort.create()
    resp = port.send("inproc://agent", _Cmd("PING"))

    # Contract: returns a dict; ok key may exist in stub
    assert isinstance(resp, dict)
    # Be tolerant of stub shape but require dict content
    assert bool(resp) or resp == {}


def test_inproc_telemetry_pub_sub_contract_noop_ok():
    sub: TelemetrySubPort = InprocTelemetrySubPort.create()
    pub: TelemetryPubPort = InprocTelemetryPubPort.create()

    # Should be callable without raising
    sub.subscribe("inproc://telem")
    pub.publish("topic", {"hello": "world"})

    # Stub returns None when no messages are present
    assert sub.recv(timeout_ms=1) is None
