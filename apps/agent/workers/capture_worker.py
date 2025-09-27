# apps/agent/workers/capture_worker.py
import threading
import time


def start_capture_worker(capture, target_fps: float) -> threading.Thread:
    stop = False

    def loop():
        nonlocal stop
        period = 1.0 / max(1e-6, target_fps)
        while not stop:
            try:
                capture.grab()
            except Exception:
                time.sleep(0.1)
            time.sleep(period * 0.5)  # light throttle; adapter also throttles

    t = threading.Thread(target=loop, name="capture-worker", daemon=True)
    t.start()
    # Return a simple object to stop if you like, or just the thread and a closure
    t._evq_stop = lambda: setattr(t, "_evq_should_stop", True)  # simplistic
    return t
