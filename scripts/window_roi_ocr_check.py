#!/usr/bin/env python3
"""
# mypy: ignore-errors
window_roi_ocr_check.py
Capture a specific client window (or any), overlay ROIs from a TOML, and optionally OCR.

Features
- Robust window selection: --index, --hwnd, --exact, or --active
- Lists all matching windows with indexes
- Clear diagnostics printing coords and chosen client rect

Usage examples:
  python window_roi_ocr_check.py --roi configs/rois/1916x1928.toml --title "Window" --list
  python window_roi_ocr_check.py --roi configs/rois/1916x1928.toml --title "Window" --index 2
      --out out1 --ocr
  python window_roi_ocr_check.py --roi configs/rois/1916x1928.toml --active --out out1
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
from ctypes import wintypes
from typing import Any

if sys.platform != "win32":
    sys.exit("This tool is Windows-only.")

# Optional imports loaded lazily in main()
Image = None
ImageDraw = None
mss = None
pytesseract = None

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
    rect = RECT()
    if not GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    pt = POINT(0, 0)
    if not ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    left, top = pt.x, pt.y
    right = left + rect.right
    bottom = top + rect.bottom
    width = rect.right
    height = rect.bottom
    return (left, top, right, bottom, width, height)


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


def _load_toml(path: str) -> dict[str, Any]:
    try:
        import tomllib  # Python 3.11+
    except Exception:
        print(
            "Python 3.11+ required for tomllib; or install tomli and edit the script.",
            file=sys.stderr,
        )
        sys.exit(3)
    with open(path, "rb") as f:
        return tomllib.load(f)


def _pct_to_px(val_pct: float | int | str, total: int) -> int:
    return int(round(float(val_pct) * float(total)))


def _roi_to_rect(roi: dict[str, Any], meta_w: int, meta_h: int) -> tuple[int, int, int, int]:
    if all(k in roi for k in ("x", "y", "w", "h")):
        x, y, w, h = int(roi["x"]), int(roi["y"]), int(roi["w"]), int(roi["h"])
        return x, y, w, h
    if all(k in roi for k in ("x_pct", "y_pct", "w_pct", "h_pct")):
        x = _pct_to_px(roi["x_pct"], meta_w)
        y = _pct_to_px(roi["y_pct"], meta_h)
        w = _pct_to_px(roi["w_pct"], meta_w)
        h = _pct_to_px(roi["h_pct"], meta_h)
        return x, y, w, h
    raise ValueError("ROI must have either (x,y,w,h) or (x_pct,y_pct,w_pct,h_pct)")


def main() -> None:
    _make_dpi_aware()

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--roi", required=True, help="Path to ROI TOML (e.g., configs/rois/1916x1928.toml)"
    )
    ap.add_argument("--out", help="Output directory (required unless --list)")
    ap.add_argument("--ocr", action="store_true", help="Run pytesseract OCR on crops")
    # selection
    ap.add_argument("--title", default="Window", help="Title substring (default: Window)")
    ap.add_argument(
        "--exact", action="store_true", help="Match title exactly (instead of substring)"
    )
    ap.add_argument("--index", type=int, help="Pick Nth match from --title search (1-based)")
    ap.add_argument("--hwnd", help="Pick by HWND (hex like 0x1234ABCD or decimal)")
    ap.add_argument("--active", action="store_true", help="Use current foreground window")
    ap.add_argument("--list", action="store_true", help="List matching windows and exit")

    args = ap.parse_args()

    # List mode
    if args.list:
        wins = _find_windows_by_title(args.title, exact=args.exact)
        if not wins:
            print(f"No visible windows matching: title={'=' if args.exact else '~'}'{args.title}'")
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
    target: int | None = None
    chosen_title: str | None = None
    if args.hwnd:
        try:
            target = int(args.hwnd, 0)
        except Exception:
            print("Invalid --hwnd value; use hex (0x...) or decimal.", file=sys.stderr)
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
                f"No visible windows matching: title={'=' if args.exact else '~'}'{args.title}'",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.index:
            idx = args.index - 1
            if not (0 <= idx < len(wins)):
                print(f"--index out of range; found {len(wins)} windows.", file=sys.stderr)
                sys.exit(2)
            target = wins[idx][0]
            chosen_title = wins[idx][1]
        else:
            target, chosen_title = wins[0]
            if len(wins) > 1:
                print("Warning: multiple matches; using first. Use --list and --index to select.")
                for i, (hw, tt) in enumerate(wins, 1):
                    print(f"  [{i}] hwnd=0x{hw:08X} title='{tt}'")

    if target is None:
        print("No target window selected.", file=sys.stderr)
        sys.exit(2)
    rect = _client_rect(target)
    if not rect:
        print("Couldn't get client rect for target window.", file=sys.stderr)
        sys.exit(2)
    left, top, _right, _bottom, w, h = rect

    print(
        f"Using hwnd=0x{target:08X}  title='{chosen_title or _get_window_text(target)}'  "
        f"client=({w}x{h}) at ({left},{top})"
    )

    if not args.out:
        print("--out is required unless using --list.", file=sys.stderr)
        sys.exit(2)

    # Lazy imports
    global Image, ImageDraw, mss, pytesseract  # module-level assignment is fine for a CLI
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:
        print("Pillow is required: pip install pillow", file=sys.stderr)
        sys.exit(4)
    try:
        import mss  # type: ignore
    except Exception:
        print("mss is required: pip install mss", file=sys.stderr)
        sys.exit(5)
    if args.ocr:
        try:
            import pytesseract  # type: ignore
        except Exception:
            print("pytesseract not found; install with: pip install pytesseract", file=sys.stderr)
            sys.exit(6)

    os.makedirs(args.out, exist_ok=True)

    # Load ROI file
    cfg = _load_toml(args.roi)
    meta = cfg.get("meta", {})
    rois: dict[str, Any] = cfg.get("rois", {})
    meta_w = int(meta.get("width", w))
    meta_h = int(meta.get("height", h))

    # Capture
    with mss.mss() as sct:  # type: ignore[attr-defined]
        monitor = {"left": left, "top": top, "width": w, "height": h}
        im = sct.grab(monitor)
        img = Image.frombytes("RGB", im.size, im.bgra, "raw", "BGRX")  # type: ignore[attr-defined]
        img.save(os.path.join(args.out, "screenshot.png"))

        boxed = img.copy()
        draw = ImageDraw.Draw(boxed)
        for name, roi in rois.items():
            try:
                rx, ry, rw, rh = _roi_to_rect(roi, meta_w, meta_h)
            except Exception as e:
                print(f"Skipping ROI '{name}': {e}", file=sys.stderr)
                continue
            draw.rectangle([(rx, ry), (rx + rw, ry + rh)], outline=(255, 0, 0), width=2)
            crop = img.crop((rx, ry, rx + rw, ry + rh))
            crop_path = os.path.join(args.out, f"roi_{name}.png")
            crop.save(crop_path)
            if args.ocr:
                text = pytesseract.image_to_string(crop)
                with open(os.path.join(args.out, f"roi_{name}.txt"), "w", encoding="utf-8") as f:
                    f.write(text.strip())

        boxed.save(os.path.join(args.out, "screenshot_boxes.png"))

    print(f"Saved capture and crops under: {args.out}")
    if args.ocr:
        print("OCR outputs saved as roi_<name>.txt alongside crops.")


if __name__ == "__main__":
    main()
