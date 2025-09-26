from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Cmd(BaseModel):
    api: Literal["v1"] = "v1"
    type: Literal["PING", "HOLD", "RESUME"]
