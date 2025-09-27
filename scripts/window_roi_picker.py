#!/usr/bin/env python3
"""
# mypy: ignore-errors
window_roi_picker.py
Live client-relative cursor coordinates & ROI picker for a chosen window.

Features
- Robust window selection: --list, --index, --hwnd, --active, --exact
- Prints the chosen HWND and client rect
- Uses ClientToScreen(origin) + GetCursorPos() to compute client-relative coords
  (more robust than ScreenToClient when DPI/focus gets weird)
- Writes/updates TOML with [meta] and [rois]; no external deps

Usage examples:
  # List candidates, then pick by index:
  python window_roi_picker.py --title "Window" --list
  python window_roi_picker.py --title "Window" --index 1 --out configs/rois/1916x1928.toml

  # Use the active (foreground) window:
  python window_roi_picker.py --active --out configs/rois/1916x1928.toml
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import time
from ctypes import wintypes
from typing import Any

if sys.platform != "win32":
    sys.exit("This tool is Windows-only.")

import msvcrt  # noqa: E402 (Windows-only console lib)

# --- DPI awareness -----------------------------------------------------------


def _make_dpi_aware() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor V2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# --- Win32 APIs --------------------------------------------------------------

user32 = ctypes.windll.user32

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
IsWindowVisible = user32.IsWindowVisible
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetClientRect = user32.GetClientRect
ClientToScreen = user32.ClientToScreen
GetCursorPos = user32.GetCursorPos
GetForegroundWindow = user32.GetForegroundWindow


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _get_window_text(hwnd: int) -> str:
    length = GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _client_rect(hwnd: int) -> tuple[int, int, int, int, int, int] | None:
    rc = RECT()
    if not GetClientRect(hwnd, ctypes.byref(rc)):
        return None
    origin = POINT(0, 0)
    if not ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    left, top = origin.x, origin.y
    width, height = rc.right, rc.bottom
    return (left, top, left + width, top + height, width, height)


def _find_windows_by_title(substr: str, exact: bool = False) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []

    def _cb(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if not title:
            return True
        t = title.lower()
        s = substr.lower()
        if (t == s) if exact else (s in t):
            matches.append((hwnd, title))
        return True

    EnumWindows(EnumWindowsProc(_cb), 0)
    return matches


def _load_toml(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:  # pragma: no cover - defensive
        print(f"Failed to read TOML ({e}); starting fresh.")
        return {}


def _dump_toml(path: str, data: dict[str, Any]) -> None:
    lines: list[str] = []
    if "meta" in data:
        meta = data["meta"]
        lines.append("[meta]")
        for k in ("name", "width", "height", "coordinate_space", "units"):
            if k in meta:
                v = meta[k]
                if isinstance(v, str):
                    lines.append(f'{k} = "{v}"')
                else:
                    lines.append(f"{k} = {v}")
        lines.append("")
    rois = data.get("rois", {}) or {}
    lines.append("[rois]")
    for name, roi in rois.items():
        if all(k in roi for k in ("x", "y", "w", "h")):
            lines.append(
                f'{name} = {{ x = {roi["x"]}, y = {roi["y"]}, ' f'w = {roi["w"]}, h = {roi["h"]} }}'
            )
        elif all(k in roi for k in ("x_pct", "y_pct", "w_pct", "h_pct")):
            lines.append(
                f'{name} = {{ x_pct = {roi["x_pct"]}, y_pct = {roi["y_pct"]}, '
                f'w_pct = {roi["w_pct"]}, h_pct = {roi["h_pct"]} }}'
            )
    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# --- CLI ---------------------------------------------------------------------


def main() -> None:
    _make_dpi_aware()

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        required=False,
        help="Output TOML path (e.g., configs/rois/1916x1928.toml)",
    )
    ap.add_argument("--title", default="Window", help="Title substring (default: Window)")
    ap.add_argument("--exact", action="store_true", help="Exact title match")
    ap.add_argument("--index", type=int, help="Pick Nth match from --title search (1-based)")
    ap.add_argument("--hwnd", help="Pick by HWND (hex 0x.. or decimal)")
    ap.add_argument("--active", action="store_true", help="Use the active (foreground) window")
    ap.add_argument("--list", action="store_true", help="List matching windows and exit")
    args = ap.parse_args()

    if args.list:
        wins = _find_windows_by_title(args.title, exact=args.exact)
        if not wins:
            print(f"No visible windows matching title={'=' if args.exact else '~'}'{args.title}'")
            sys.exit(1)
        print(f"Found {len(wins)} window(s):")
        for i, (hwnd, title) in enumerate(wins, 1):
            rect = _client_rect(hwnd)
            if rect:
                left, top, _right, _bottom, width, height = rect
                print(
                    f"[{i}] hwnd=0x{hwnd:08X}  title='{title}'  client=({width}x{height}) at "
                    + f"({left},{top})"
                )
            else:
                print(f"[{i}] hwnd=0x{hwnd:08X}  title='{title}'  client=(?)")
        sys.exit(0)

    # Resolve target hwnd
    if args.hwnd:
        try:
            target = int(args.hwnd, 0)
        except Exception:
            print("Invalid --hwnd; use hex (0x...) or decimal.", file=sys.stderr)
            sys.exit(2)
    elif args.active:
        target = GetForegroundWindow()
        if not target:
            print("No foreground window.", file=sys.stderr)
            sys.exit(2)
    else:
        wins = _find_windows_by_title(args.title, exact=args.exact)
        if not wins:
            print(
                f"No visible windows matching title={'=' if args.exact else '~'}'{args.title}'",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.index:
            idx = args.index - 1
            if not (0 <= idx < len(wins)):
                print(f"--index out of range; found {len(wins)} windows.", file=sys.stderr)
                sys.exit(2)
            target, _chosen_title = wins[idx]
        else:
            target, _chosen_title = wins[0]
            if len(wins) > 1:
                print("Warning: multiple matches; using first. Use --list and --index to choose.")
                for i, (hw, tt) in enumerate(wins, 1):
                    print(f"  [{i}] hwnd=0x{hw:08X}  title='{tt}'")

    rect = _client_rect(target)
    if not rect:
        print("Couldn't get client rect.", file=sys.stderr)
        sys.exit(2)
    left, top, _right, _bottom, w, h = rect
    print(
        f"Using hwnd=0x{target:08X}  title='{_get_window_text(target)}'  "
        f"client=({w}x{h}) at ({left},{top})"
    )

    if not args.out:
        print("Note: --out not provided; coordinates will not be saved. (Picker shows live XY)")

    # Load TOML
    data = _load_toml(args.out) if args.out else {"meta": {"width": w, "height": h}, "rois": {}}
    if "meta" not in data:
        data["meta"] = {
            "name": "Window",
            "width": w,
            "height": h,
            "coordinate_space": "client",
            "units": "px",
        }
    if "rois" not in data:
        data["rois"] = {}
    if args.out:
        _dump_toml(args.out, data)
        print(f"Writing to: {args.out}")

    tl: tuple[int, int] | None = None
    br: tuple[int, int] | None = None

    print(
        "\nControls: '1' mark TL, '2' mark BR, 'n' name+save, 'f' full ROI, 'r' reload+print, "
        + "'q' quit.\n"
    )
    print("Live client-relative cursor coords will stream every ~100ms.\n")

    last_print = 0.0
    while True:
        now = time.time()
        if now - last_print > 0.1:
            last_print = now
            cur = POINT()
            GetCursorPos(ctypes.byref(cur))
            origin = POINT(0, 0)
            ClientToScreen(target, ctypes.byref(origin))
            cx = cur.x - origin.x
            cy = cur.y - origin.y
            sys.stdout.write(f"\rCursor (client): x={cx:4d}  y={cy:4d}    TL={tl}  BR={br}   ")
            sys.stdout.flush()

        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch.lower() == "q":
                print("\nExiting.")
                break
            if ch == "1":
                cur = POINT()
                GetCursorPos(ctypes.byref(cur))
                origin = POINT(0, 0)
                ClientToScreen(target, ctypes.byref(origin))
                tl = (cur.x - origin.x, cur.y - origin.y)
                print(f"\nMarked TL = {tl}")
            elif ch == "2":
                cur = POINT()
                GetCursorPos(ctypes.byref(cur))
                origin = POINT(0, 0)
                ClientToScreen(target, ctypes.byref(origin))
                br = (cur.x - origin.x, cur.y - origin.y)
                print(f"\nMarked BR = {br}")
            elif ch.lower() == "n":
                if not args.out:
                    print("\nProvide --out to save ROIs.")
                    continue
                if not (tl and br):
                    print("\nMark TL ('1') and BR ('2') first.")
                    continue
                x0, y0 = tl
                x1, y1 = br
                x = min(x0, x1)
                y = min(y0, y1)
                wroi = abs(x1 - x0)
                hroi = abs(y1 - y0)
                name = input("\nROI name: ").strip()
                if name:
                    data = _load_toml(args.out) or {"meta": {"width": w, "height": h}, "rois": {}}
                    data.setdefault("rois", {})
                    data["rois"][name] = {"x": x, "y": y, "w": wroi, "h": hroi}
                    _dump_toml(args.out, data)
                    print(f"Saved ROI '{name}' = x:{x} y:{y} w:{wroi} h:{hroi}")
                else:
                    print("No name entered; skipped.")
            elif ch.lower() == "f":
                if not args.out:
                    print("\nProvide --out to save ROIs.")
                    continue
                data = _load_toml(args.out) or {"meta": {"width": w, "height": h}, "rois": {}}
                data["rois"]["full"] = {"x": 0, "y": 0, "w": w, "h": h}
                _dump_toml(args.out, data)
                print(f"\nSet 'full' ROI to 0,0,{w},{h}")
            elif ch.lower() == "r":
                if not args.out:
                    print("\nProvide --out to reload.")
                    continue
                data = _load_toml(args.out)
                print("\nCurrent ROIs:")
                for k, v in (data.get("rois") or {}).items():
                    print(f"  - {k}: {v}")

        time.sleep(0.01)


if __name__ == "__main__":
    main()
