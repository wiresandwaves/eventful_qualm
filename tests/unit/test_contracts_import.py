from __future__ import annotations

from shared.contracts.v1.telemetry import Telemetry


def test_contracts_import():
    t = Telemetry(agent_id="vm1", state="ASSIST", ts=0.0)
    assert t.api == "v1"
