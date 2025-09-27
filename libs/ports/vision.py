# libs/ports/vision.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

ROI = tuple[int, int, int, int]  # x, y, w, h  (compat alias)


@dataclass(frozen=True)
class Frame:
    width: int
    height: int
    # raw BGRA bytes (row-major). Keep it tech-agnostic.
    bgra: bytes

    def size(self) -> tuple[int, int]:
        return self.width, self.height


class CapturePort(Protocol):
    def open(self, target: str | None = None) -> None: ...
    def grab(self) -> Frame: ...
    def grab_roi(self, roi: tuple[int, int, int, int]) -> Frame: ...  # x,y,w,h
    def fps(self) -> float: ...
    def close(self) -> None: ...
