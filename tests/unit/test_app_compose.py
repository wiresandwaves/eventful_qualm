from __future__ import annotations

from apps.agent.compose import AgentApp
from apps.agent.settings import AgentSettings
from apps.coordinator.compose import CoordinatorApp
from apps.coordinator.settings import CoordinatorSettings


def test_agent_compose():
    app = AgentApp(AgentSettings(agent_id="vmX"))
    assert app.settings.agent_id == "vmX"


def test_coordinator_compose():
    app = CoordinatorApp(CoordinatorSettings(refresh_hz=2.0))
    assert app.settings.refresh_hz == 2.0
