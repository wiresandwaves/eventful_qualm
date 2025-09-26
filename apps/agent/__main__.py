from __future__ import annotations

import argparse
import time
from typing import Any

from shared.config.loader import load_agent_settings

from apps.agent.compose import build_ipc


def _handler_factory(telem_pub):
    """Return a simple command handler. Publishes a heartbeat on PING."""

    def handle(cmd: dict[str, Any]) -> dict[str, Any]:
        ctype = (cmd or {}).get("type", "")
        if ctype == "PING":
            # minimal visibility: publish a heartbeat
            try:
                telem_pub.publish("heartbeat", {"ok": True})
            except Exception:
                pass
            return {"pong": True}
        return {"echo": ctype or "UNKNOWN"}

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
            f"telem_bind={getattr(settings, 'telem_bind', '?')}"
        )

    handler = _handler_factory(telem_pub)

    try:
        while True:
            # Poll once for a command; if none, loop quickly
            try:
                cmd_server.poll_once(handler)
            except Exception as ex:
                if not args.quiet:
                    print(f"[agent] handler error: {ex!r}")
            time.sleep(max(args.tick_ms, 1) / 1000.0)
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
