from __future__ import annotations

from adapters.dx_capture import FakeScreenCapturePort
from adapters.ipc_zmq import FakeAgentCommandPort, FakeTelemetrySubPort
from adapters.telemetry import FakeMetricsPort, FakeTelemetryPort
from adapters.time import FakeClockPort, FakeSleeperPort
from adapters.win_input import FakeFocusPort, FakeHumanInputPort, FakeKeyboardMousePort


def test_input_fakes():
    kbd = FakeKeyboardMousePort()
    kbd.tap_scancode(0x11)  # 'W' scancode example
    assert len(kbd.keys) == 2
    kbd.key_up_all()  # should not crash even if none pressed

    human = FakeHumanInputPort()
    seen = {"count": 0}
    human.subscribe(lambda: seen.__setitem__("count", seen["count"] + 1))
    human.trigger()
    assert seen["count"] == 1

    focus = FakeFocusPort()
    assert focus.ensure_foreground() is True
    assert focus.times_called == 1


def test_capture_fake():
    cap = FakeScreenCapturePort(fps_value=42.0)
    frame = cap.grab()
    assert frame.ts >= 0.0
    assert cap.fps() == 42.0


def test_ipc_fakes_roundtrip():
    cmd = FakeAgentCommandPort()
    out = cmd.send("agent://a", {"type": "PING"})
    assert out.get("ok") is True

    sub = FakeTelemetrySubPort()
    sub.subscribe("agent://a")
    sub.inject({"agent_id": "a", "state": "ASSIST"})
    rec = sub.recv(200)
    assert rec and rec["agent_id"] == "a"


def test_telemetry_and_metrics():
    telem = FakeTelemetryPort()
    telem.publish({"agent_id": "a", "state": "HOLD"})
    assert telem.records and telem.records[0]["state"] == "HOLD"

    metrics = FakeMetricsPort()
    metrics.observe("tick_ms", 12.5, agent="a")
    assert metrics.samples[0][0] == "tick_ms"


def test_time_fakes():
    clk = FakeClockPort()
    t1 = clk.now()
    slp = FakeSleeperPort()
    slp.sleep(0.01)
    t2 = clk.now()
    assert t2 >= t1
