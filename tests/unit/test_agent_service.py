from __future__ import annotations

from adapters.telemetry import FakeTelemetryPort
from adapters.time import FakeClockPort, FakeSleeperPort
from domain.agent import AgentService


def test_tick_publishes_telem_and_respects_hold():
    clock = FakeClockPort()
    sleep = FakeSleeperPort()
    telem = FakeTelemetryPort()
    svc = AgentService(clock, sleep, telem, agent_id="vmT", heartbeat_hz=10.0)

    svc.tick()
    assert telem.records, "first tick should publish telemetry"
    assert telem.records[-1]["state"] == "ASSIST"

    svc.set_hold(True)
    svc.tick()
    assert telem.records[-1]["state"] == "HOLD"
