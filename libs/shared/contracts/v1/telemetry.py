from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Telemetry(BaseModel):
    api: Literal["v1"] = "v1"
    agent_id: str
    state: Literal["ACTIVE", "ASSIST", "HOLD"]
    hp: int | None = None
    mana: int | None = None
    ts: float
    fps: float | None = None
