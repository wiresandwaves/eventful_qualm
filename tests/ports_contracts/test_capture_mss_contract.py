# tests/ports_contracts/test_capture_mss_contract.py
import importlib

import pytest

mss_available = importlib.util.find_spec("mss") is not None

pytestmark = pytest.mark.contract


@pytest.mark.skipif(not mss_available, reason="mss not installed")
def test_grab_has_nonzero_dims():
    from libs.adapters.dx_capture.mss import MSSCapture

    cap = MSSCapture(monitor=1, target_fps=5.0)
    cap.open()
    try:
        frame = cap.grab()
        assert frame.width > 0 and frame.height > 0
        assert len(frame.bgra) == frame.width * frame.height * 4  # BGRA
    finally:
        cap.close()


@pytest.mark.skipif(not mss_available, reason="mss not installed")
def test_grab_roi_dims_match():
    from libs.adapters.dx_capture.mss import MSSCapture

    cap = MSSCapture(monitor=1, target_fps=5.0)
    cap.open()
    try:
        roi = (10, 10, 120, 80)
        frame = cap.grab_roi(roi)
        assert (frame.width, frame.height) == (120, 80)
    finally:
        cap.close()


@pytest.mark.skipif(not mss_available, reason="mss not installed")
def test_fps_increases_when_grabbing_loop():
    from libs.adapters.dx_capture.mss import MSSCapture

    cap = MSSCapture(monitor=1, target_fps=10.0)
    cap.open()
    try:
        for _ in range(6):
            _ = cap.grab()
        assert cap.fps() > 0.0
    finally:
        cap.close()
