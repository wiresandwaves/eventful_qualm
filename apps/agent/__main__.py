from __future__ import annotations

import argparse
import importlib
import threading
import time
from typing import Any, Protocol, cast

from shared.config.loader import load_agent_settings

from apps.agent.compose import build_ipc


class _HasCapture(Protocol):
    def open(self) -> None: ...
    def grab(self) -> object: ...
    def fps(self) -> float: ...
    def close(self) -> None: ...


class _AgentState:
    __slots__ = ("hold",)

    def __init__(self) -> None:
        self.hold: bool = False


def _make_capture(settings) -> _HasCapture | None:
    try:
        mod = importlib.import_module("adapters.dx_capture.mss")
        MSSCaptureAny = cast(Any, mod.MSSCapture)
    except Exception:
        return None

    cap = cast(
        _HasCapture,
        MSSCaptureAny(
            monitor=getattr(settings.capture, "monitor", 1),
            target_fps=getattr(settings.capture, "target_fps", 10.0),
        ),
    )
    cap.open()
    return cap


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
            _publish("state", {"state": "ASSIST", "hold": False})
            return {"ok": True, "agent_id": agent_id, "hold": False}
        # Unknown command
        _publish("event", {"note": "unknown_command", "type": ctype or "UNKNOWN"})
        return {"echo": ctype or "UNKNOWN", "agent_id": agent_id, "hold": state.hold}

    return handle


def _start_capture_worker(settings) -> tuple[_HasCapture | None, threading.Thread | None]:
    cap = _make_capture(settings)
    if cap is None:
        return None, None

    stop_flag = {"stop": False}

    def loop():
        period = 1.0 / max(1e-6, getattr(settings.capture, "target_fps", 10.0))
        while not stop_flag["stop"]:
            try:
                cap.grab()
            except Exception:
                time.sleep(0.1)
            time.sleep(period * 0.5)

    t = threading.Thread(target=loop, name="capture-worker", daemon=True)
    t.start()

    def _stop() -> None:
        stop_flag["stop"] = True

    t._evq_stop = _stop  # type: ignore[attr-defined]
    return cap, t


def main() -> int:
    ap = argparse.ArgumentParser(prog="eventful-qualm-agent")
    ap.add_argument("--tick-ms", type=int, default=10, help="Loop sleep between polls.")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output.")
    args = ap.parse_args()

    settings = load_agent_settings()  # uses your loader/env/profile
    cmd_server, telem_pub = build_ipc(settings)
    capture: _HasCapture | None
    cap_thr: threading.Thread | None
    capture, cap_thr = _start_capture_worker(settings)

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
                    payload = {
                        "ok": True,
                        "agent_id": settings.agent_id,
                        "hold": state.hold,
                    }
                    if capture is not None:
                        try:
                            payload["fps"] = float(capture.fps())
                        except Exception:
                            pass
                    telem_pub.publish("heartbeat", payload)
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
        try:
            if cap_thr is not None and hasattr(cap_thr, "_evq_stop"):
                stopper = cap_thr._evq_stop
                if callable(stopper):
                    stopper()
            if capture is not None:
                capture.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
