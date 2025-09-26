from __future__ import annotations

from pydantic import BaseModel, Field


class CoordinatorSettings(BaseModel):
    refresh_hz: float = Field(default=5.0)
    # REQ connects to these per agent_id
    agents_cmd: dict[str, str] = Field(default_factory=lambda: {"vm1": "tcp://127.0.0.1:7788"})
    # SUB connects to each of these
    telem_subs: list[str] = Field(default_factory=lambda: ["tcp://127.0.0.1:7789"])
