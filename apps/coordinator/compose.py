from __future__ import annotations

import asyncio
import logging
from typing import Final

from adapters.ipc_zmq import FakeAgentCommandPort, FakeTelemetrySubPort
from adapters.time import FakeClockPort

from apps.coordinator.settings import CoordinatorSettings

LOG: Final = logging.getLogger("coordinator")


class CoordinatorApp:
    def __init__(self, settings: CoordinatorSettings) -> None:
        self.settings = settings
        self.clock = FakeClockPort()
        self.cmd = FakeAgentCommandPort()
        self.sub = FakeTelemetrySubPort()  # in-process fake queue
        self._running = True

    async def seed_fake_stream(self) -> None:
        """In-process telemetry generator for demo; replaced by real ZMQ in M5."""
        LOG.info("Starting fake telemetry generator.")
        t = 0
        while self._running:
            # Simulate two agents publishing
            now = self.clock.now()
            self.sub.inject({"agent_id": "vm1", "state": "ASSIST", "ts": now})
            self.sub.inject(
                {"agent_id": "vm2", "state": "HOLD" if t % 10 == 0 else "ASSIST", "ts": now}
            )
            t += 1
            await asyncio.sleep(0.2)

    async def ui_loop(self) -> None:
        """Tiny text UI; prints last-seen per agent at a fixed rate."""
        LOG.info("Coordinator UI starting.")
        refresh = 1.0 / max(0.5, self.settings.refresh_hz)
        last: dict[str, dict] = {}
        try:
            while self._running:
                # Drain any telemetry quickly
                while True:
                    rec = self.sub.recv(timeout_ms=1)
                    if rec is None:
                        break
                    last[rec["agent_id"]] = rec

                # Render a minimal table
                if last:
                    lines = ["\n=== Dalaya Coordinator ==="]
                    for aid in sorted(last):
                        r = last[aid]
                        lines.append(f"{aid:>4}  state={r.get('state')}  age=0.0s")
                    print("\n".join(lines), end="\r", flush=True)
                await asyncio.sleep(refresh)
        except asyncio.CancelledError:
            LOG.info("Coordinator UI cancelled.")
        except KeyboardInterrupt:
            LOG.info("Coordinator interrupted; shutting down.")
        finally:
            self._running = False
