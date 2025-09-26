from __future__ import annotations

from pydantic import BaseModel, Field


class AgentSettings(BaseModel):
    agent_id: str = Field(default="vm1")
    heartbeat_hz: float = Field(default=5.0)
    # IPC endpoints (used by later milestones; safe defaults today)
    cmd_bind: str = Field(default="tcp://127.0.0.1:7788")
    telem_bind: str = Field(default="tcp://127.0.0.1:7789")
