from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoordinatorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVQ_", extra="ignore")

    refresh_hz: float = 5.0

    # choose transport impl
    ipc_impl: Literal["inproc", "zmq"] = "inproc"

    agents_cmd: dict[str, str] = {}  # name -> REQ endpoint
    telem_subs: list[str] = []  # list of SUB endpoints
