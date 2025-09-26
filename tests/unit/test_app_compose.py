from __future__ import annotations

from ports.ipc import AgentCommandPort, TelemetryPubPort, TelemetrySubPort

from apps.agent.compose import build_ipc as build_agent_ipc
from apps.agent.settings import AgentSettings
from apps.coordinator.compose import build_ipc as build_coord_ipc
from apps.coordinator.settings import CoordinatorSettings


def test_agent_compose_inproc():
    settings = AgentSettings(agent_id="vmX", ipc_impl="inproc")
    cmd_port, telem_pub = build_agent_ipc(settings)

    # Settings wired correctly
    assert settings.agent_id == "vmX"

    # Interface types
    assert isinstance(cmd_port, AgentCommandPort)
    assert isinstance(telem_pub, TelemetryPubPort)

    # publish() exists and is callable (no guarantees about delivery in inproc stub)
    telem_pub.publish("heartbeat", {"ok": True})


def test_coordinator_compose_inproc():
    settings = CoordinatorSettings(refresh_hz=2.0, ipc_impl="inproc")
    cmd_port, telem_sub = build_coord_ipc(settings)

    # Settings wired correctly
    assert settings.refresh_hz == 2.0

    # Interface types
    assert isinstance(cmd_port, AgentCommandPort)
    assert isinstance(telem_sub, TelemetrySubPort)

    # subscribe() + non-blocking recv() should not raise for inproc stub
    telem_sub.subscribe("inproc://telem")
    assert telem_sub.recv(timeout_ms=1) is None
