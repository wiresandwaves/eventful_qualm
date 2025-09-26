from ports.ipc import AgentCommandPort, TelemetryPubPort

from apps.agent.settings import AgentSettings


def build_ipc(settings: AgentSettings) -> tuple[AgentCommandPort, TelemetryPubPort]:
    cmd: AgentCommandPort
    telem_pub: TelemetryPubPort

    if settings.ipc_impl == "zmq":
        from adapters.ipc_zmq.zmq import ZmqAgentCommandPort, ZmqTelemetryPubPort

        # Agent side: REP bind for commands; PUB bind for telemetry
        cmd = ZmqAgentCommandPort.bind_rep(settings.cmd_bind)
        telem_pub = ZmqTelemetryPubPort.bind_pub(settings.telem_bind)
    else:
        from adapters.ipc_inproc.inproc import InprocAgentCommandPort, InprocTelemetryPubPort

        cmd = InprocAgentCommandPort.create()
        telem_pub = InprocTelemetryPubPort.create()
    return cmd, telem_pub
