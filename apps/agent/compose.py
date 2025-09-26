# apps/agent/compose.py
from __future__ import annotations

from adapters.dx_capture import FakeScreenCapturePort
from adapters.telemetry import FakeTelemetryPort
from adapters.time import FakeClockPort, FakeSleeperPort
from adapters.win_input import FakeFocusPort, FakeHumanInputPort, FakeKeyboardMousePort
from domain.agent import AgentService

from apps.agent.settings import AgentSettings


class AgentApp:
    """Wires the domain service to fake adapters only."""

    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings

        # Fakes (no OS calls)
        self.clock = FakeClockPort()
        self.sleep = FakeSleeperPort()
        self.telemetry = FakeTelemetryPort()
        self.human = FakeHumanInputPort()
        self.focus = FakeFocusPort()
        self.kbm = FakeKeyboardMousePort()
        self.capture = FakeScreenCapturePort(fps_value=30.0)

        # Domain service
        self.svc = AgentService(
            clock=self.clock,
            sleep=self.sleep,
            telem=self.telemetry,
            agent_id=self.settings.agent_id,
            heartbeat_hz=self.settings.heartbeat_hz,
        )

        # Manual override: any human input flips HOLD
        self.human.subscribe(lambda: self.svc.set_hold(True))

    def heartbeat_once(self) -> None:
        self.svc.tick()

    @property
    def period(self) -> float:
        return self.svc.period
