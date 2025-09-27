# tests/unit/test_telemetry.py

import pytest
from pydantic import ValidationError
from shared.contracts.v1.telemetry import Telemetry


def test_api_defaults_to_v1():
    t = Telemetry(agent_id="a1", state="ASSIST", ts=123.0)
    assert t.api == "v1"


def test_telemetry_fps_is_optional_and_defaults_none():
    t = Telemetry(agent_id="a1", state="ASSIST", ts=123.0)
    assert t.fps is None


def test_telemetry_allows_setting_fps():
    t = Telemetry(agent_id="a1", state="ACTIVE", ts=123.0, fps=27.5)
    assert t.fps == pytest.approx(27.5, rel=1e-6)


def test_state_literal_is_enforced():
    with pytest.raises(ValidationError):
        Telemetry(agent_id="a1", state="RUN", ts=1.0)  # type: ignore[arg-type]
