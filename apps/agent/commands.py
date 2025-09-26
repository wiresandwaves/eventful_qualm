from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AgentCommandDispatcher:
    def __init__(self) -> None:
        self._routes: dict[str, Callable[[dict], dict]] = {}

    def route(self, cmd_type: str):
        def deco(fn: Callable[[dict], dict]):
            self._routes[cmd_type.upper()] = fn
            return fn

        return deco

    def handle(self, cmd: dict[str, Any]) -> dict[str, Any]:
        t = (cmd or {}).get("type", "")
        fn = self._routes.get(str(t).upper())
        if not fn:
            return {"echo": t or "UNKNOWN"}
        return fn(cmd)
