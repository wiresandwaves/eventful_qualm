# tests/e2e/test_agent_smoke.py
from __future__ import annotations

from apps.agent.compose import AgentApp
from apps.agent.settings import AgentSettings


def test_agent_smoke_heartbeat():
    app = AgentApp(AgentSettings(agent_id="vmS", heartbeat_hz=20.0))
    app.heartbeat_once()
    recs = app.telemetry.records
    assert recs and recs[-1]["agent_id"] == "vmS"
