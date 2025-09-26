from __future__ import annotations

from ports.ipc import AgentCommandPort, CommandServerPort, TelemetryPubPort, TelemetrySubPort

from apps.agent.compose import build_ipc as build_agent_ipc
from apps.agent.settings import AgentSettings
from apps.coordinator.compose import build_ipc as build_coord_ipc
from apps.coordinator.settings import CoordinatorSettings


def test_agent_compose_inproc():
    settings = AgentSettings(agent_id="vmX", ipc_impl="inproc")
    cmd_server, telem_pub = build_agent_ipc(settings)

    assert settings.agent_id == "vmX"
    # Runtime-checkable Protocol lets us isinstance-check
    assert isinstance(cmd_server, CommandServerPort)
    assert isinstance(telem_pub, TelemetryPubPort)


def test_coordinator_compose_inproc():
    settings = CoordinatorSettings(refresh_hz=2.0, ipc_impl="inproc")
    cmd_port, telem_sub = build_coord_ipc(settings)

    assert settings.refresh_hz == 2.0
    assert isinstance(cmd_port, AgentCommandPort)
    assert isinstance(telem_sub, TelemetrySubPort)
