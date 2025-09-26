from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVQ_", extra="ignore")

    agent_id: str = "vm1"
    heartbeat_hz: float = 5.0

    # choose transport impl
    ipc_impl: Literal["inproc", "zmq"] = "inproc"

    # Already present in your profiles:
    cmd_bind: str = "tcp://127.0.0.1:7788"
    telem_bind: str = "tcp://127.0.0.1:7789"
