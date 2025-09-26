# ADR 0005 - IPC Wire Spec (ZeroMQ)

- Status: Accepted
- Date: 2025-09-25
- Deciders: Project Owner
- Tags: ipc, zeromq, contracts, reliability

## Context
ADR-0002 chose ZeroMQ for its low boilerplate and great local performance. We now freeze the **concrete wire spec** so adapters, tests, and config can be implemented predictably, and future changes are versioned.

## Decision
Use **REQ/REP** for commands (Coordinator &rarr; Agent) and **PUB/SUB** for telemetry (Agent &rarr; Coordinator), with **JSON messages** validated by Pydantic models and a mandatory version field `api: "v1"`.

### Sockets & Roles
- **Agent (inside VM)**
  - `REP` bind at `cmd_bind` (default `tcp://0.0.0.0:7788`)
    Receives command requests; replies with JSON `{ok: bool, ...}`.
  - `PUB` bind at `telem_bind` (default `tcp://0.0.0.0:7789`)
    Publishes telemetry JSON (no topic; `SUBSCRIBE ""` is fine).

- **Coordinator (host)**
  - `REQ` connect to `agents_cmd[agent_id]`
  - `SUB` connect to each `telem_subs[*]` and `SUBSCRIBE ""`

### Messages (JSON, UTF-8)
**Commands (Coordinator &rarr; Agent)**
~~~json
{ "api": "v1", "type": "PING" }
{ "api": "v1", "type": "HOLD" }
{ "api": "v1", "type": "RESUME" }
~~~
**Response (Agent &rarr; Coordinator)**
~~~json
{ "ok": true, "echo": { "api": "v1", "type": "PING" } }
~~~

**Telemetry (Agent &rarr; Coordinator)** &mdash; matches `shared.contracts.v1.Telemetry`
~~~json
{
  "api": "v1",
  "agent_id": "vm1",
  "state": "ASSIST",
  "hp": null,
  "mana": null,
  "ts": 12345.678
}
~~~

### Timeouts, Retries, Backoff (REQ/REP)
- `REQ` poll for reply: **500 ms** per attempt.
- Retries: **3** attempts with backoff **100 ms, 200 ms, 400 ms** (cap at 1 s).
- On total failure: return `{ "ok": false, "err": "timeout" }` and log a warning.
- `REP` must reply once per request; malformed JSON &rarr; `{ "ok": false, "err": "bad-json" }`.

### Startup Order & Warm-Up
- Agent **binds** (REP, PUB) first; Coordinator then **connects** (REQ, SUB).
- After `PUB.bind`, sleep **50 ms** to avoid initial drop on Windows.

### Versioning
- All payloads include `"api": "v1"`.
- On bump to `v2`, adapters accept only their version and reject mismatches:
  - Commands: `{ "ok": false, "err": "api-mismatch" }`
  - Telemetry: drop with a logged warning.

### Configuration
- `apps/agent/settings.py`
  - `agent_id: str = "vm1"`
  - `heartbeat_hz: float = 5.0`
  - `cmd_bind: str = "tcp://0.0.0.0:7788"`
  - `telem_bind: str = "tcp://0.0.0.0:7789"`
- `apps/coordinator/settings.py`
  - `refresh_hz: float = 5.0`
  - `agents_cmd: dict[str, str] = { "vm1": "tcp://127.0.0.1:7788" }`
  - `telem_subs: list[str] = [ "tcp://127.0.0.1:7789" ]`
- Profiles live in `configs/profiles/*.toml` (see ADR-0003), overridable via env `EVQ_*`.

### Error Handling & Logging
- Coordinator:
  - WARN on command timeout; surface `{ok:false}` to UI.
- Agent:
  - WARN on unknown command types; reply `{ "ok": false, "err": "unknown" }`.
  - Malformed JSON: `{ "ok": false, "err": "bad-json" }`.

### Minimal Contract Tests (Required)
- **REQ/REP**: `PING` round-trip `{ok:true}` within **500 ms**.
- **PUB/SUB**: telemetry observed within **200 ms** (after PUB warm-up).
- **Malformed JSON**: `{ok:false, err:"bad-json"}`.
- **Unknown command**: `{ok:false, err:"unknown"}`.
- **API mismatch**: commands `{ok:false, err:"api-mismatch"}`; coordinator drops telemetry.

### Security
- Local/lab use only; bind to trusted interfaces (127.0.0.1 or host-only networks).
  If needed later, add ZMQ CURVE or migrate to gRPC/TLS.

## Consequences
- :white_check_mark: Simple, fast local IPC with tiny adapter code.
- :white_check_mark: Predictable behavior under timeouts and malformed messages.
- :heavy_minus_sign: No built-in schemas on the wire; mitigated by Pydantic + version field.

## Alternatives Considered
- **gRPC**: stronger contracts/streaming but heavier for our 2-agent local scenario; keep as plan B.

## Rollout Plan
1. Implement ZMQ adapters conforming to this spec behind existing ports.
2. Add the contract tests above under `tests/port_contracts/` (mark `@pytest.mark.contract`).
3. Wire apps to use **real IPC** with a flag/env to choose fake vs real.
