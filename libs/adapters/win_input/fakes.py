from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from ports.input import FocusPort, HumanInputPort, KeyboardMousePort, KeyEvent, MousePathPoint


@dataclass(frozen=True)
class KeyEventRecord:
    scan: int
    down: bool


@dataclass(frozen=True)
class MousePathRecord:
    path: tuple[tuple[int, int, int], ...]  # (x, y, t_ms) tuples


class FakeKeyboardMousePort(KeyboardMousePort):
    """Records what would have been sent to the OS."""

    def __init__(self) -> None:
        self.keys: list[KeyEventRecord] = []
        self.paths: list[MousePathRecord] = []
        self._pressed: set[int] = set()

    def tap_scancode(self, scan: int, down_ms: int = 45) -> None:
        self.keys.append(KeyEventRecord(scan=scan, down=True))
        self.keys.append(KeyEventRecord(scan=scan, down=False))

    def send_keys(self, events: Iterable[KeyEvent]) -> None:
        for e in events:
            self.keys.append(KeyEventRecord(scan=e.scan, down=e.down))
            if e.down:
                self._pressed.add(e.scan)
            else:
                self._pressed.discard(e.scan)

    def mouse_path(self, path: Sequence[MousePathPoint]) -> None:
        self.paths.append(MousePathRecord(path=tuple((p.x, p.y, p.t_ms) for p in path)))

    def key_up_all(self) -> None:
        # Emit key-up records for everything currently pressed
        for scan in sorted(self._pressed):
            self.keys.append(KeyEventRecord(scan=scan, down=False))
        self._pressed.clear()


class FakeHumanInputPort(HumanInputPort):
    """Simple pub/sub for 'human activity' events."""

    def __init__(self) -> None:
        self._subs: list[Callable[[], None]] = []

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._subs.append(callback)

    # Test helper: trigger all subscribers
    def trigger(self) -> None:
        for cb in list(self._subs):
            cb()


class FakeFocusPort(FocusPort):
    def __init__(self, will_focus: bool = True) -> None:
        self.times_called = 0
        self.will_focus = will_focus

    def ensure_foreground(self) -> bool:
        self.times_called += 1
        return self.will_focus
