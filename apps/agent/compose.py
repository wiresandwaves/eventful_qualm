from __future__ import annotations

from adapters.dx_capture.mss import MSSCapture
from domain.agent.service import AgentService
from ports.ipc import CommandServerPort, TelemetryPubPort
from ports.vision import CapturePort

from apps.agent.settings import AgentSettings


def build_ipc(settings: AgentSettings) -> tuple[CommandServerPort, TelemetryPubPort]:
    cmd_server: CommandServerPort
    telem_pub: TelemetryPubPort

    if settings.ipc_impl == "zmq":
        from adapters.ipc_zmq import ZmqAgentCommandPort, ZmqTelemetryPubPort

        cmd_server = ZmqAgentCommandPort.bind_rep(settings.cmd_bind)
        telem_pub = ZmqTelemetryPubPort.bind_pub(settings.telem_bind)
    else:
        from adapters.ipc_inproc import InprocCommandServerPort, InprocTelemetryPubPort

        cmd_server = InprocCommandServerPort.create()
        telem_pub = InprocTelemetryPubPort.create()

    return cmd_server, telem_pub


def build_capture(cfg) -> CapturePort:
    if cfg.capture.adapter == "mss":
        return MSSCapture(monitor=cfg.capture.monitor, target_fps=cfg.capture.target_fps)
    raise ValueError(f"Unknown capture adapter: {cfg.capture.adapter}")


def build_agent(settings, clock, sleeper, telem):
    capture = MSSCapture(
        monitor=settings.capture.monitor,
        target_fps=settings.capture.target_fps,
    )
    capture.open()  # make sure it’s ready

    svc = AgentService(
        clock=clock,
        sleep=sleeper,
        telem=telem,
        agent_id=settings.agent_id,
        heartbeat_hz=settings.heartbeat_hz,
        perf=capture,  # <-- just pass it
    )
    return svc, capture
