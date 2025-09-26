import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any, cast

import zmq
from ports.ipc import AgentCommandPort, TelemetryPubPort, TelemetrySubPort
from shared.contracts.v1.ipc_wire import (
    SCHEMA_V1,
    CommandEnvelope,
    ErrorInfo,
    ResponseEnvelope,
    TelemetryEnvelope,
)

# --------- Common helpers ---------


def _new_ctx() -> zmq.Context:
    # Using the global instance avoids thread-happy leaks and is cheap.
    return zmq.Context.instance()


def _set_common(sock: zmq.Socket, rcv_ms: int = 500, snd_ms: int = 500) -> None:
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.RCVTIMEO, rcv_ms)
    sock.setsockopt(zmq.SNDTIMEO, snd_ms)


# --------- AgentCommandPort (REQ client + REP server) ---------


class ZmqAgentCommandPort(AgentCommandPort):
    """
    Coordinator-side REQ client for commands.
    Agent-side REP server is provided via bind_rep(...).
    """

    def __init__(self) -> None:
        self._ctx = _new_ctx()
        self._req_cache: dict[str, zmq.Socket] = {}

    @classmethod
    def bind_rep(cls, addr: str) -> "ZmqAgentCommandREPServer":
        return ZmqAgentCommandREPServer(addr=addr)

    def _get_req(self, addr: str) -> zmq.Socket:
        s = self._req_cache.get(addr)
        if s is None:
            s = self._ctx.socket(zmq.REQ)
            _set_common(s)
            s.connect(addr)
            self._req_cache[addr] = s
        return s

    def send(self, addr: str, cmd) -> dict[str, Any]:
        """
        Sends a CommandEnvelope-like dict and expects a ResponseEnvelope-like dict back.
        Retries once on timeout.
        """
        msg_id = str(uuid.uuid4())
        env = CommandEnvelope(msg_id=msg_id, command={"type": getattr(cmd, "type", "UNKNOWN")})
        payload = env.model_dump(mode="json")

        s = self._get_req(addr)

        for attempt in (1, 2):
            try:
                s.send_json(payload)
                return cast(dict[str, Any], s.recv_json())
            except zmq.error.Again:
                if attempt == 2:
                    return ResponseEnvelope(
                        ok=False,
                        correlates_to=msg_id,
                        error=ErrorInfo(code="timeout", detail="REQ timeout"),
                    ).model_dump()
                try:
                    s.close(0)
                except Exception:
                    pass
                self._req_cache.pop(addr, None)
                s = self._get_req(addr)
            except Exception as ex:
                return ResponseEnvelope(
                    ok=False,
                    correlates_to=msg_id,
                    error=ErrorInfo(code="internal", detail=repr(ex)),
                ).model_dump()
        # Should not reach.
        return ResponseEnvelope(
            ok=False,
            correlates_to=msg_id,
            error=ErrorInfo(code="internal", detail="unreachable"),
        ).model_dump()


@dataclass
class ZmqAgentCommandREPServer:
    """
    Agent-side REP server binder. You call `poll_once(handler)` or `serve_for(seconds, handler)`
    from your agent loop/thread to process command requests.
    """

    addr: str

    def __post_init__(self) -> None:
        self._ctx = _new_ctx()
        self._sock = self._ctx.socket(zmq.REP)
        _set_common(self._sock)
        self._sock.bind(self.addr)

    def close(self) -> None:
        try:
            self._sock.close(0)
        finally:
            pass

    def poll_once(self, handler) -> bool:
        """
        Poll for one request; if present, process with handler(command_dict) -> response_dict.
        Returns True if a message was processed, False on idle.
        """
        try:
            if not self._sock.poll(timeout=10):
                return False

            # Got something; try to receive JSON
            try:
                req = self._sock.recv_json()
            except Exception:
                self._sock.send_json(
                    {
                        "ok": False,
                        "correlates_to": "<unknown>",
                        "error": {"code": "bad-json", "detail": "Invalid JSON"},
                    }
                )
                return True

            # Validate schema_version
            if int(req.get("schema_version", 0)) != SCHEMA_V1:
                self._sock.send_json(
                    {
                        "ok": False,
                        "correlates_to": req.get("msg_id", "<unknown>"),
                        "error": {"code": "api-mismatch", "detail": "schema_version != 1"},
                    }
                )
                return True

            # Dispatch
            cmd = req.get("command") or {}
            msg_id = req.get("msg_id", "<unknown>")

            try:
                result = handler(cmd) or {}
                self._sock.send_json({"ok": True, "correlates_to": msg_id, "data": result})
            except Exception as ex:
                self._sock.send_json(
                    {
                        "ok": False,
                        "correlates_to": msg_id,
                        "error": {"code": "internal", "detail": repr(ex)},
                    }
                )
            return True

        except zmq.error.Again:
            return False

    def serve_for(self, seconds: float, handler) -> None:
        deadline = monotonic() + seconds
        while monotonic() < deadline:
            self.poll_once(handler)


# --------- Telemetry (PUB/SUB) ---------


class ZmqTelemetryPubPort(TelemetryPubPort):
    def __init__(self, addr: str) -> None:
        self._ctx = _new_ctx()
        self._pub = self._ctx.socket(zmq.PUB)
        _set_common(self._pub)
        self._pub.bind(addr)

    @classmethod
    def bind_pub(cls, addr: str) -> "ZmqTelemetryPubPort":
        return cls(addr)

    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        env = TelemetryEnvelope(msg_id=str(uuid.uuid4()), topic=topic, data=dict(payload))
        self._pub.send_multipart(
            [
                topic.encode("utf-8"),
                json.dumps(env.model_dump(mode="json")).encode("utf-8"),
            ]
        )


class ZmqTelemetrySubPort(TelemetrySubPort):
    def __init__(self) -> None:
        self._ctx = _new_ctx()
        self._sub = self._ctx.socket(zmq.SUB)
        _set_common(self._sub)
        # Allow all topics by default
        self._sub.setsockopt(zmq.SUBSCRIBE, b"")
        # Prevent unbounded growth
        self._sub.setsockopt(zmq.RCVHWM, 1000)

    def subscribe(self, addr: str) -> None:
        self._sub.connect(addr)

    def recv(self, timeout_ms: int = 100) -> dict[str, Any] | None:
        if self._sub.poll(timeout=timeout_ms):
            topic, data = self._sub.recv_multipart()
            try:
                decoded = json.loads(data.decode("utf-8"))
            except Exception:
                return {"topic": topic.decode("utf-8"), "error": {"code": "bad-json"}}
            # keep return type as dict for the port; payload is a TelemetryEnvelope dict
            return {
                "topic": topic.decode("utf-8"),
                "data": decoded.get("data", {}),
                "envelope": decoded,
            }
        return None
