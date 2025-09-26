from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AgentState = Literal["ACTIVE", "ASSIST", "HOLD"]


@dataclass
class AgentContext:
    agent_id: str
    state: AgentState
    last_ts: float | None = None
