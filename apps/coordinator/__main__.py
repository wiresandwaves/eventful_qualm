from __future__ import annotations

import asyncio
import logging
import sys

from apps.coordinator.compose import CoordinatorApp
from apps.coordinator.settings import CoordinatorSettings


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def _amain() -> int:
    _setup_logging()
    settings = CoordinatorSettings()
    app = CoordinatorApp(settings)

    # Run fake generator + UI concurrently
    task_gen = asyncio.create_task(app.seed_fake_stream())
    task_ui = asyncio.create_task(app.ui_loop())
    try:
        await asyncio.gather(task_gen, task_ui)
    finally:
        task_gen.cancel()
        task_ui.cancel()
    return 0


def main() -> int:
    try:
        return asyncio.run(_amain())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
