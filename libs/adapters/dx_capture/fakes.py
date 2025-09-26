from __future__ import annotations

from typing import Any

from adapters.time.fakes import FakeClockPort
from ports.vision import ROI, Frame, ScreenCapturePort


class FakeScreenCapturePort(ScreenCapturePort):
    """Returns a dummy Frame; rgba is None for now to avoid numpy dependency."""

    def __init__(self, fps_value: float = 30.0) -> None:
        self._fps = float(fps_value)
        self._clock = FakeClockPort()

    def grab(self, roi: ROI | None = None) -> Frame:
        # rgba can be set to None or a simple placeholder; domain shouldn’t assume ndarray yet.
        rgba: Any = None
        return Frame(rgba=rgba, ts=self._clock.now())

    def fps(self) -> float:
        return self._fps
