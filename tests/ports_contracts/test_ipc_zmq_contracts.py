from __future__ import annotations

import socket
import threading
import time
from contextlib import closing
from time import perf_counter

import pytest

try:
    import zmq  # noqa: F401
except Exception:
    pytest.skip("pyzmq not installed", allow_module_level=True)

from adapters.ipc_zmq import ZmqAgentCommandPort, ZmqTelemetryPubPort, ZmqTelemetrySubPort


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])  # explicit int()


def _cmd_handler(cmd: dict) -> dict:
    t = (cmd or {}).get("type", "")
    if t == "PING":
        return {"pong": True}
    # You can expand handlers later (HOLD, RESUME, etc.)
    return {"echo": t}


def _run_rep_server(addr: str, stop_event: threading.Event):
    rep = ZmqAgentCommandPort.bind_rep(addr)
    try:
        while not stop_event.is_set():
            rep.poll_once(_cmd_handler)
            # yield a tick
            time.sleep(0.001)
    finally:
        rep.close()


def _endpoints() -> tuple[str, str]:
    a = f"tcp://127.0.0.1:{_free_port()}"
    b = f"tcp://127.0.0.1:{_free_port()}"
    return a, b


class _Cmd:
    def __init__(self, t: str) -> None:
        self.type = t


def test_zmq_ping_under_500ms():
    cmd_ep, _ = _endpoints()

    stop = threading.Event()
    th = threading.Thread(target=_run_rep_server, args=(cmd_ep, stop), daemon=True)
    th.start()
    try:
        client = ZmqAgentCommandPort()
        t0 = perf_counter()
        resp = client.send(cmd_ep, _Cmd("PING"))
        dt = perf_counter() - t0

        assert isinstance(resp, dict)
        assert resp.get("ok") is True
        assert resp.get("data", {}).get("pong") is True
        assert dt < 0.5, f"Round-trip too slow: {dt:.3f}s"
    finally:
        stop.set()
        th.join(timeout=1.0)


def test_zmq_bad_json_error():
    cmd_ep, _ = _endpoints()

    stop = threading.Event()
    th = threading.Thread(target=_run_rep_server, args=(cmd_ep, stop), daemon=True)
    th.start()
    try:
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.setsockopt(zmq.LINGER, 0)
        s.setsockopt(zmq.RCVTIMEO, 500)
        s.setsockopt(zmq.SNDTIMEO, 500)
        s.connect(cmd_ep)

        # Send non-JSON bytes to simulate malformed message
        s.send(b"\x80\x81\x82")
        resp = s.recv_json()
        assert resp.get("ok") is False
        assert resp.get("error", {}).get("code") == "bad-json"
    finally:
        stop.set()
        th.join(timeout=1.0)


def test_zmq_api_mismatch_error():
    cmd_ep, _ = _endpoints()

    stop = threading.Event()
    th = threading.Thread(target=_run_rep_server, args=(cmd_ep, stop), daemon=True)
    th.start()
    try:
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.setsockopt(zmq.LINGER, 0)
        s.setsockopt(zmq.RCVTIMEO, 500)
        s.setsockopt(zmq.SNDTIMEO, 500)
        s.connect(cmd_ep)

        bad = {"schema_version": 999, "msg_id": "x", "command": {"type": "PING"}}
        s.send_json(bad)
        resp = s.recv_json()
        assert resp.get("ok") is False
        assert resp.get("error", {}).get("code") == "api-mismatch"
    finally:
        stop.set()
        th.join(timeout=1.0)


def test_zmq_telemetry_receive():
    _, telem_ep = _endpoints()

    pub = ZmqTelemetryPubPort.bind_pub(telem_ep)
    sub = ZmqTelemetrySubPort()
    sub.subscribe(telem_ep)

    # Give SUB a moment to connect (classic PUB/SUB pattern)
    time.sleep(0.05)

    pub.publish("heartbeat", {"ok": True, "fps": 60})

    # Allow up to 500 ms for delivery
    end = time.time() + 0.5
    got = None
    while time.time() < end and got is None:
        got = sub.recv(timeout_ms=50)

    assert got is not None, "Did not receive telemetry within timeout"
    assert got.get("topic") == "heartbeat"
    assert got.get("data", {}).get("ok") is True
    assert got.get("data", {}).get("fps") == 60
