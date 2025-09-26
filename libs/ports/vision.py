from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NamedTuple


class ROI(NamedTuple):
    x: int
    y: int
    w: int
    h: int


class Frame(NamedTuple):
    rgba: Any  # placeholder for an image buffer (e.g., ndarray)
    ts: float


class ScreenCapturePort(ABC):
    @abstractmethod
    def grab(self, roi: ROI | None = None) -> Frame: ...

    @abstractmethod
    def fps(self) -> float: ...


class OCRPort(ABC):
    @abstractmethod
    def read_text(self, image: Any, lang: str = "eng") -> str: ...


class TemplateMatchPort(ABC):
    @abstractmethod
    def match(
        self, image: Any, template: Any, threshold: float = 0.95
    ) -> tuple[int, int] | None: ...
