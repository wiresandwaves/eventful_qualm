from __future__ import annotations

import time

from adapters.ipc_zmq import FakeAgentCommandPort, FakeTelemetrySubPort


def test_command_send_returns_ok():
    cmd = FakeAgentCommandPort()
    out = cmd.send("agent://vm1", {"type": "PING"})
    assert out.get("ok") is True
    # sent payload recorded per-address
    assert cmd.sent["agent://vm1"]["type"] == "PING"


def test_fake_sub_receives_within_500ms():
    sub = FakeTelemetrySubPort()
    sub.subscribe("agent://vm1")  # no-op for fake, but mirrors the real API

    # inject a heartbeat and assert we can recv it within 0.5s
    t0 = time.perf_counter()
    sub.inject({"agent_id": "vm1", "state": "ASSIST", "ts": t0})

    rec = None
    deadline = t0 + 0.5
    while rec is None and time.perf_counter() < deadline:
        rec = sub.recv(timeout_ms=50)

    assert rec is not None, "No telemetry received within 500ms"
    assert rec["agent_id"] == "vm1"
    assert rec["state"] == "ASSIST"
