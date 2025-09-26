# ADR 0004 - Testing Strategy (Fakes, Contract Tests, Replay)

- Status: Accepted
- Date: 2025-09-25
- Deciders: Project Owner
- Tags: testing, quality, ci

## Context
We want confidence without flaky UI-bound tests. Early development uses fakes (no Windows APIs). Later we add integration tests with real adapters. We also want deterministic regression tests for behavior logic (BT/HFSM) using recorded replays.

## Decision
Adopt a layered test strategy:

1. **Unit tests (domain & helpers)**
   - Pure functions/state machines; no I/O.
   - Targets: `libs/domain`, `libs/shared/utils`.

2. **Port-contract tests (adapters)**
   - Each adapter must satisfy its port under expected scenarios.
   - Start with **fake adapters** to define the contract.
   - Later add **real adapters** (e.g., ZeroMQ, dxcam) under the same tests (via pytest marks).

3. **Replay tests (deterministic)**
   - Record short sessions: screen frames (or frame hashes), log tail text, and input/telemetry timelines into a `.everrec` bundle (zip or folder).
   - Re-run domain logic against the replay to validate decisions without live game/windows.
   - Keep clips short (60–120s) to stay fast in CI.

4. **End-to-end smoke**
   - Minimal: start Agent (fake or real IPC) + Coordinator; verify telemetry appears and PING returns ok.
   - Run on CI (Windows runner) and keep under ~10s.

### Repo structure
~~~
tests/
  unit/                # pure domain/utils
  port_contracts/      # fakes + (later) real adapters under marks
  replay/              # deterministic scenarios against recorded data
  e2e/                 # minimal process-level smoke tests
~~~

### Pytest conventions
- Markers:
  - `@pytest.mark.contract` — port contracts
  - `@pytest.mark.replay`   — replay-driven
  - `@pytest.mark.e2e`      — process-level smokes
- Default CI run excludes slow/real-hardware marks:
  - `-m "not e2e and not slow"`

### Replay format (v0)
- Container: directory or zip (`.everrec`)
- Contents:
  - `meta.json` — schema version, resolution, timestamps
  - `logs/` — raw game log slices
  - `frames/` — PNG frames or hashes (to avoid huge repos)
  - `inputs.jsonl` — synthetic input timeline (if needed)
  - `telemetry.jsonl` — expected telemetry for assertions

### SLAs (indicative)
- Unit: < 300 ms each
- Contract: < 1 s each
- Replay suite: ≤ 15 s total
- E2E smoke: ≤ 10 s

## Consequences
- :white_check_mark: High confidence early via fakes; same tests exercise real adapters later.
- :white_check_mark: Deterministic behavior validation via replay.
- :heavy_minus_sign: Small tooling to record/pack replays; curate clips to keep CI fast.

## Alternatives Considered
- Full UI automation only — too flaky/slow early on.
- Unit tests only — insufficient for adapters and IPC.

## Implementation Notes
- Provide `tools/record_replay/` to capture frames/hashes + logs to `.everrec`.
- Add `libs/shared/utils/replay.py` helpers to iterate replays in tests.
- CI: run unit + contract by default; run replay and e2e on main or nightly.
