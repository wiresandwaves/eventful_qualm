from __future__ import annotations

from ports.ipc import CommandServerPort, TelemetryPubPort

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
