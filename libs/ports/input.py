from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from typing import Protocol


class KeyEvent(Protocol):
    scan: int
    down: bool


class MousePathPoint(Protocol):
    x: int
    y: int
    t_ms: int  # time from start


class KeyboardMousePort(ABC):
    """Abstract input device; domain never sees SendInput directly."""

    @abstractmethod
    def tap_scancode(self, scan: int, down_ms: int = 45) -> None: ...

    @abstractmethod
    def send_keys(self, events: Iterable[KeyEvent]) -> None: ...

    @abstractmethod
    def mouse_path(self, path: Sequence[MousePathPoint]) -> None: ...

    @abstractmethod
    def key_up_all(self) -> None: ...


class HumanInputPort(ABC):
    """Signals when the *human* touches mouse/keyboard."""

    @abstractmethod
    def subscribe(self, callback: Callable[[], None]) -> None: ...

    # callback is a no-arg function returning None


class FocusPort(ABC):
    """Bring target window to foreground if required."""

    @abstractmethod
    def ensure_foreground(self) -> bool: ...
