# ADR 0002 — IPC Messaging Choice (ZeroMQ first, gRPC later if needed)

- Status: Accepted
- Date: 2025-09-24
- Deciders: Project Owner
- Tags: ipc, messaging, networking

## Context
We need host/agent communication for commands (HOLD/RESUME/PING) and telemetry (HP/mana/state).
Constraints: max two agents, local network/host-only, rapid iteration, simple deployment.

## Decision
Use ZeroMQ initially:
- Agent exposes a REP socket for commands and a PUB socket for telemetry.
- Coordinator connects via REQ/SUB.
- Messages are small JSON with explicit version (v1), validated by Pydantic.

Upgrade path to gRPC if we need stronger contracts/streaming/language interop later.

## Consequences
- Positive: Minimal boilerplate; great for local sockets; fast iteration.
- Negative: No built-in schema; we mitigate with JSON models + versioning. Backpressure/retries are app-level.

## Alternatives Considered
- gRPC (protobuf): strong contracts/streaming, but heavier startup friction for our scale today.
- Raw TCP/WebSockets: flexible but reinvents patterns already solved by ZMQ.
