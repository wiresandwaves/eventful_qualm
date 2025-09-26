from __future__ import annotations

import argparse
import time

from shared.config.loader import load_agent_settings

from apps.agent.commands import AgentCommandDispatcher
from apps.agent.compose import build_ipc


def _make_dispatcher(telem_pub, hb_period_s: float):
    disp = AgentCommandDispatcher()

    @disp.route("PING")
    def _ping(_cmd: dict) -> dict:
        try:
            telem_pub.publish("heartbeat", {"ok": True})
        except Exception:
            pass
        return {"pong": True}

    # you can add HOLD/RESUME later
    return disp


def main() -> int:
    ap = argparse.ArgumentParser(prog="eventful-qualm-agent")
    ap.add_argument("--tick-ms", type=int, default=10, help="Loop sleep between polls.")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output.")
    args = ap.parse_args()

    settings = load_agent_settings()  # uses your loader/env/profile
    cmd_server, telem_pub = build_ipc(settings)

    hb_period_s = 1.0 / max(settings.heartbeat_hz, 0.1)
    disp = _make_dispatcher(telem_pub, hb_period_s)

    next_hb = time.monotonic() + hb_period_s
    tick_s = max(args.tick_ms, 1) / 1000.0

    try:
        while True:
            # drive commands
            try:
                cmd_server.poll_once(disp.handle)
            except Exception as ex:
                if not args.quiet:
                    print(f"[agent] handler error: {ex!r}")

            # periodic heartbeat
            now = time.monotonic()
            if now >= next_hb:
                try:
                    telem_pub.publish("heartbeat", {"ok": True})
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
