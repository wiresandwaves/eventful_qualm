# libs/domain/agent/service.py
from __future__ import annotations

from typing import Final

from ports.perf import PerfPort
from ports.telemetry import TelemetryPort
from ports.time import ClockPort, SleeperPort
from shared.contracts.v1.telemetry import Telemetry

from .model import AgentContext


class AgentService:
    """Pure domain service (no OS calls). Decides and emits telemetry."""

    def __init__(
        self,
        clock: ClockPort,
        sleep: SleeperPort,
        telem: TelemetryPort,
        agent_id: str,
        heartbeat_hz: float = 5.0,
        perf: PerfPort | None = None,
    ) -> None:
        self.clock: Final = clock
        self.sleep: Final = sleep
        self.telem: Final = telem
        self.perf: Final = perf
        self.ctx = AgentContext(agent_id=agent_id, state="ASSIST")
        self._period = 1.0 / max(0.1, heartbeat_hz)
        self._hold = False

    def set_hold(self, value: bool) -> None:
        self._hold = bool(value)

    def tick(self) -> None:
        """One iteration: compute state + publish telemetry."""
        now = self.clock.now()
        state = "HOLD" if self._hold else self.ctx.state
        fps_value = self.perf.fps() if self.perf else None
        self.telem.publish(
            Telemetry(
                agent_id=self.ctx.agent_id,
                state=state,
                hp=None,
                mana=None,
                ts=now,
                fps=fps_value,
            )
        )
        self.ctx.last_ts = now

    @property
    def period(self) -> float:
        return self._period
