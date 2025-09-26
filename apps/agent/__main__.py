from __future__ import annotations

import logging
import sys
import time

from shared.config.loader import load_agent_settings

from apps.agent.compose import AgentApp


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_agent_settings()  # reads profile + env
    app = AgentApp(settings)

    try:
        while True:
            app.heartbeat_once()
            if app.telemetry.records:
                rec = app.telemetry.records[-1]
                logging.info(
                    "heartbeat: id=%s state=%s ts=%.3f",
                    rec["agent_id"],
                    rec["state"],
                    rec["ts"],
                )
            time.sleep(app.period)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
