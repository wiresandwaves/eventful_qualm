# ADR 0003 - Configuration Strategy (Pydantic Settings + Profiles)

- Status: Accepted
- Date: 2025-09-25
- Deciders: Project Owner
- Tags: config, pydantic, environments

## Context
We need consistent, typed configuration across two apps (Agent, Coordinator) and multiple environments (dev, vm1, vm2). Config must be:

- Typed/validated at startup (fail fast).
- Layered (defaults -> profile files -> env vars -> CLI).
- Portable for CI/VMs and simple to override locally.

## Decision
Use Pydantic Settings (v2) for typed config classes, with this precedence:

1. Code defaults in AgentSettings / CoordinatorSettings
2. Profile TOML files in `configs/profiles/` (loaded by profile name)
3. Environment variables (prefix: `EVQ_`)
4. CLI flags (optional later; applied last)

### File layout
~~~
configs/
  profiles/
    dev.toml
    vm1.toml
    vm2.toml
  rois/
    1600x900.toml
  keymaps/
    default.toml
~~~

### Naming conventions
- Env var prefix: `EVQ_` (e.g., `EVQ_CMD_BIND`, `EVQ_TELEM_BIND`).
- Profile selection: `EVQ_PROFILE=vm1` (or CLI `--profile vm1` later).
- TOML keys mirror settings model fields (snake_case).

### Example `configs/profiles/vm1.toml`
~~~toml
[agent]
agent_id = "vm1"
heartbeat_hz = 5.0
cmd_bind = "tcp://0.0.0.0:7788"
telem_bind = "tcp://0.0.0.0:7789"

[coordinator]
refresh_hz = 5.0
agents_cmd = { vm1 = "tcp://127.0.0.1:7788" }
telem_subs = ["tcp://127.0.0.1:7789"]
~~~

### Loading order (at app start)
1. Instantiate settings with code defaults.
2. If `EVQ_PROFILE` is set (default `dev`), load `configs/profiles/<profile>.toml` and update fields.
3. Overlay environment variables (`EVQ_*`).
4. (Future) Overlay CLI flags.

### Validation
- Pydantic validates types/ranges on creation.
- If invalid, log a clear error and exit non-zero.

### Rationale
- Pydantic Settings provides robust validation with minimal boilerplate.
- TOML profiles keep environment configs versioned and reviewable.
- Env vars make VM/container deployment simple.

## Consequences
- :white_check_mark: Clear precedence & strong typing.
- :heavy_minus_sign: Small loader helper needed; keep profile docs current.

## Alternatives Considered
- dotenv / env-only — simple but untyped and hard to review.
- YAML + manual parsing — more code, less safety.
- Hydra / Dynaconf — powerful, heavier than needed.

## Implementation Notes
- Add `libs/shared/config/loader.py` to:
  - read `EVQ_PROFILE` (default `dev`);
  - merge TOML -> env -> CLI;
  - return populated `AgentSettings` / `CoordinatorSettings`.
- Add README examples for env/profile usage.
