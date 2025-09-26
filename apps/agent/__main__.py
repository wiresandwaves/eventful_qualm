from __future__ import annotations

import argparse
import time
from typing import Any

from shared.config.loader import load_agent_settings

from apps.agent.compose import build_ipc


class _AgentState:
    __slots__ = ("hold",)

    def __init__(self) -> None:
        self.hold: bool = False


def _make_dispatcher(telem_pub, agent_id: str, state: _AgentState):
    """Return a function(cmd_dict)->dict that handles
    PING/HOLD/RESUME and tags telemetry with agent_id."""

    def _publish(topic: str, payload: dict[str, Any]) -> None:
        # Ensure outgoing telemetry always carries agent_id (non-breaking)
        data = {"agent_id": agent_id, **payload}
        try:
            telem_pub.publish(topic, data)
        except Exception:
            pass

    def handle(cmd: dict[str, Any]) -> dict[str, Any]:
        ctype = (cmd or {}).get("type", "").upper()
        if ctype == "PING":
            _publish("heartbeat", {"ok": True})
            return {"pong": True, "agent_id": agent_id, "hold": state.hold}
        if ctype == "HOLD":
            state.hold = True
            _publish("state", {"state": "HOLD", "hold": True})
            return {"ok": True, "agent_id": agent_id, "hold": True}
        if ctype == "RESUME":
            state.hold = False
            _publish("state", {"state": "RUN", "hold": False})
            return {"ok": True, "agent_id": agent_id, "hold": False}
        # Unknown command
        _publish("event", {"note": "unknown_command", "type": ctype or "UNKNOWN"})
        return {"echo": ctype or "UNKNOWN", "agent_id": agent_id, "hold": state.hold}

    return handle


def main() -> int:
    ap = argparse.ArgumentParser(prog="eventful-qualm-agent")
    ap.add_argument("--tick-ms", type=int, default=10, help="Loop sleep between polls.")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output.")
    args = ap.parse_args()

    settings = load_agent_settings()  # uses your loader/env/profile
    cmd_server, telem_pub = build_ipc(settings)

    if not args.quiet:
        print(
            f"[agent] ipc_impl={settings.ipc_impl} "
            f"cmd_bind={getattr(settings, 'cmd_bind', '?')} "
            f"telem_bind={getattr(settings, 'telem_bind', '?')} "
            f"agent_id={settings.agent_id}"
        )

    state = _AgentState()
    handle = _make_dispatcher(telem_pub, settings.agent_id, state)

    hb_period_s = 1.0 / max(getattr(settings, "heartbeat_hz", 1.0), 0.1)
    next_hb = time.monotonic() + hb_period_s
    tick_s = max(args.tick_ms, 1) / 1000.0

    try:
        while True:
            try:
                cmd_server.poll_once(handle)
            except Exception as ex:
                if not args.quiet:
                    print(f"[agent] handler error: {ex!r}")

            now = time.monotonic()
            if now >= next_hb:
                # periodic heartbeat
                try:
                    telem_pub.publish(
                        "heartbeat", {"ok": True, "agent_id": settings.agent_id, "hold": state.hold}
                    )
                except Exception:
                    pass
                next_hb = now + hb_period_s

            time.sleep(tick_s)
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n[agent] shutting down...")
    finally:
        try:
            cmd_server.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
