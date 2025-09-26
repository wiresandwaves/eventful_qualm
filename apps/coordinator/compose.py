from ports.ipc import AgentCommandPort, TelemetrySubPort

from apps.coordinator.settings import CoordinatorSettings


def build_ipc(settings: CoordinatorSettings) -> tuple[AgentCommandPort, TelemetrySubPort]:
    cmd: AgentCommandPort
    telem_sub: TelemetrySubPort

    if settings.ipc_impl == "zmq":
        from adapters.ipc_zmq.zmq import ZmqAgentCommandPort, ZmqTelemetrySubPort

        cmd = ZmqAgentCommandPort()  # REQ socket; will connect per send(addr, ...)
        telem_sub = ZmqTelemetrySubPort()
        for ep in settings.telem_subs:
            telem_sub.subscribe(ep)
    else:
        from adapters.ipc_inproc.inproc import InprocAgentCommandPort, InprocTelemetrySubPort

        cmd = InprocAgentCommandPort.create()
        telem_sub = InprocTelemetrySubPort.create()
    return cmd, telem_sub
