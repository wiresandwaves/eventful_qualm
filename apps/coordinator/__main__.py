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
    ap.add_argument("--hold", metavar="AGENT", help="Send HOLD to agent and exit.")
    ap.add_argument("--resume", metavar="AGENT", help="Send RESUME to agent and exit.")
    ap.add_argument("--tui", action="store_true", help="Run the Textual TUI.")
    args = ap.parse_args()
    topics = {t.strip() for t in args.topics.split(",") if t.strip()} if args.topics else set()

    if args.tui:
        # Launch the TUI app; it builds its own IPC via the loader.
        from apps.coordinator.tui import CoordinatorTUI

        app = CoordinatorTUI()
        app.run()
        return 0

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

    def _one_shot(verb: str, agent: str) -> int:
        ep = settings.agents_cmd.get(agent)
        if not ep:
            print(f"[coord] unknown agent '{agent}'. Known: {sorted(settings.agents_cmd.keys())}")
            return 2
        resp = cmd_port.send(ep, SimpleNamespace(type=verb))
        print(f"[coord] {verb}->{agent} @ {ep} :: {resp}")
        return 0

    if args.hold:
        return _one_shot("HOLD", args.hold)
    if args.resume:
        return _one_shot("RESUME", args.resume)

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
