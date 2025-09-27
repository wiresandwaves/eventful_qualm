from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any, cast

try:
    import mss  # type: ignore
except Exception:  # pragma: no cover
    mss = None

from ports.vision import CapturePort, Frame

Rect = Mapping[str, int]  # {"left": int, "top": int, "width": int, "height": int}


class MSSCapture(CapturePort):
    def __init__(self, monitor: int = 1, target_fps: float = 10.0) -> None:
        self._monitor_idx = int(monitor)
        self._target_fps = float(target_fps)
        self._sct: mss.mss | None = None
        self._mon: dict[str, int] | None = None
        self._last_times: list[float] = []

    def open(self, target: str | None = None) -> None:  # target unused
        if mss is None:
            raise RuntimeError("mss is not installed")
        sct = mss.mss()
        monitors = sct.monitors  # has attribute at runtime
        # clamp to a real monitor (monitors[0] is "all")
        idx = self._monitor_idx
        if idx < 1 or idx >= len(monitors):
            idx = 1
        mon = cast(dict[str, int], dict(monitors[idx]))
        self._sct = sct
        self._mon = mon

    def _grab_rect(self, rect: Rect) -> Frame:
        assert self._sct is not None
        shot: Any = self._sct.grab(rect)
        # Prefer BGRA if available; fall back to raw/rgb
        if hasattr(shot, "bgra"):
            bgra_bytes = bytes(shot.bgra)
        elif hasattr(shot, "raw"):
            bgra_bytes = bytes(shot.raw)
        else:
            bgra_bytes = bytes(shot.rgb)
        return Frame(width=shot.width, height=shot.height, bgra=bgra_bytes)

    def grab(self) -> Frame:
        if self._sct is None or self._mon is None:
            self.open()
        sct = self._sct
        mon = self._mon
        assert sct is not None and mon is not None
        frame = self._grab_rect(mon)
        self._maybe_sleep()
        self._tick_fps()
        return frame

    def grab_roi(self, roi: tuple[int, int, int, int]) -> Frame:
        if self._sct is None or self._mon is None:
            self.open()
        mon = self._mon
        assert mon is not None
        x, y, w, h = roi
        rect: dict[str, int] = {
            "left": int(mon["left"]) + int(x),
            "top": int(mon["top"]) + int(y),
            "width": int(w),
            "height": int(h),
        }
        frame = self._grab_rect(rect)
        self._maybe_sleep()
        self._tick_fps()
        return frame

    def fps(self) -> float:
        now = time.perf_counter()
        self._last_times = [t for t in self._last_times if now - t <= 1.0]
        return float(len(self._last_times))

    def close(self) -> None:
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
        self._sct = None
        self._mon = None
        self._last_times.clear()

    def _maybe_sleep(self) -> None:
        if self._target_fps > 0:
            time.sleep(max(0.0, (1.0 / self._target_fps) * 0.25))

    def _tick_fps(self) -> None:
        self._last_times.append(time.perf_counter())
