# ADR 0007 — Adapter Naming & Fakes Policy

- **Status:** Proposed
- **Date:** 2025-09-26
- **Deciders:** Project Owner
- **Tags:** naming, testing, adapters

## Context
We previously used a “fake vs real” naming convention to bootstrap. We want production code to be named **sensibly by technology/transport**, not by “real”, and we want to keep fakes only as test aids. This matches how IPC adapters are already named (`ipc_inproc`, `ipc_zmq`).

This ADR formalizes naming and location so code stays clean and discoverable across Hexagonal boundaries (ADR-0001) and our testing strategy (ADR-0004).

## Decision
1) **Adapters are named by technology or protocol**, never by “real”.
   - Examples: `dx_capture/mss.py`, `dx_capture/dxcam.py`, `win_input/sendinput.py`, `ocr_tesseract/tesseract.py`, `ipc_zmq/zmq.py`.
2) **Fakes live alongside adapters** as `fakes.py` (or explicit `fake_*.py`) and are used only in tests or local dev profiles.
3) **Composition chooses adapters via config**, not imports that reference “fake” or “real”.
4) **Docs and code comments** avoid the “real” label; working implementations are assumed real by default.

## Rationale
- Keeps production names stable and meaningful; avoids “real vs real2”.
- Cleanly supports multiple tech back-ends (e.g., MSS and DXGI) under one port.
- Aligns with ports/adapters architecture and the layered test strategy.

## Conventions

**Directory layout:**
~~~
libs/
  adapters/
    dx_capture/
      __init__.py
      mss.py           # tech-named concrete
      dxcam.py         # alternate concrete
      fakes.py         # test doubles only
    win_input/
      __init__.py
      sendinput.py
      fakes.py
    ipc_zmq/
      __init__.py
      zmq.py
    ipc_inproc/
      __init__.py
      inproc.py
~~~

**Config selection (per ADR-0003):**
~~~toml
[agent.capture]
adapter = "mss"      # not "real" / "fake"
~~~

**Tests (per ADR-0004):**
- Port contracts run against fakes first, then real adapters under marks.
- Fakes are importable in tests but should not be wired in production compose.

## Consequences
- :white_check_mark: Clear, stable names in code and config.
- :white_check_mark: Easier to maintain multiple real adapters per port.
- :heavy_minus_sign: Minor refactors to rename any lingering “real” symbols (one-time).

## Alternatives Considered
- Keep “real”/“fake” suffixes: rejected—ambiguous and scales poorly with multiple real implementations.

## Rollout
1) Update any lingering references to “real” in docs or code comments to tech-named modules.
2) Ensure compose paths read adapter names from config consistently.
3) Keep existing fakes for CI/contract tests; don’t expose them via production config.
