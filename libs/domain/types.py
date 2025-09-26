from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentState:
    agent_id: str
    state: str
    hp: int | None
    mana: int | None
    ts: float
