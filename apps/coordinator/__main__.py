from __future__ import annotations

import argparse
import time
from types import SimpleNamespace

from shared.config.loader import load_coordinator_settings

from apps.coordinator.compose import build_ipc


def main() -> int:
    ap = argparse.ArgumentParser(prog="eventful-qualm-coordinator")
    ap.add_argument("--ping", metavar="AGENT", help="Agent name to ping once and exit (e.g., vm1).")
    ap.add_argument("--watch", action="store_true", help="Print telemetry messages until Ctrl+C.")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output.")
    ap.add_argument(
        "--connect-wait-ms", type=int, default=100, help="PUB/SUB settle time before first recv."
    )
    ap.add_argument(
        "--topics",
        default="",
        help="Comma-separated list of topic filters (e.g., heartbeat,roi,fps).",
    )
    args = ap.parse_args()
    topics = {t.strip() for t in args.topics.split(",") if t.strip()} if args.topics else set()

    settings = load_coordinator_settings()  # uses your loader/env/profile
    cmd_port, telem_sub = build_ipc(settings)

    if not args.quiet:
        print(
            f"[coord] ipc_impl={settings.ipc_impl} "
            f"agents_cmd={getattr(settings, 'agents_cmd', {})} "
            f"telem_subs={getattr(settings, 'telem_subs', [])}"
        )

    # Give SUB a brief moment to connect before first publish/receive
    time.sleep(max(args.connect_wait_ms, 0) / 1000.0)

    # Optional one-shot ping
    if args.ping:
        ep = settings.agents_cmd.get(args.ping)
        if not ep:
            print(
                f"[coord] unknown agent '{args.ping}'. Known: {sorted(settings.agents_cmd.keys())}"
            )
            return 2
        resp = cmd_port.send(ep, SimpleNamespace(type="PING"))
        if not args.quiet:
            print(f"[coord] PING->{args.ping} @ {ep} :: {resp}")
        else:
            print(resp)
        if not args.watch:
            return 0

    # Telemetry tail
    if args.watch:
        try:
            while True:
                msg = telem_sub.recv(timeout_ms=250)
                if not msg:
                    continue
                if topics and msg.get("topic") not in topics:
                    continue
                if not args.quiet:
                    print(f"[coord] TELEM <- {msg}")
        except KeyboardInterrupt:
            if not args.quiet:
                print("\n[coord] exiting.")
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
