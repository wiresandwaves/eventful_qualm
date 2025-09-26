# ADR 0006 — Screen Capture Adapter (MSS first, DXGI later)

- **Status:** Proposed  
- **Date:** 2025-09-26  
- **Deciders:** Project Owner  
- **Tags:** capture, adapters, windows, performance

## Context
We’re ready to feed the agent with real screen pixels so we can measure loop cadence (FPS) and later do ROI parsing/OCR. The architecture expects a capture **port** with swappable **adapters** per Hexagonal Architecture. We also want to surface FPS via telemetry, which the Coordinator TUI already displays.

Requirements:
- Run **inside each Agent VM** (Windows).
- Provide whole-screen and ROI capture; expose a simple FPS metric.
- Be easy to get running first (:arrow_right: reliability over peak perf), with a path to a higher-perf adapter later.

Related ADRs / docs: hex architecture (0001), config strategy (0003), testing strategy (0004), IPC wire spec (0005), diagrams.

## Decision
1) Define/confirm a **capture port** in `libs/ports/vision.py` (already present) with a minimal API (see “Port API”).
2) Implement a reliable baseline adapter named by **technology**, not “real”:
   - `libs/adapters/dx_capture/mss.py` using the `mss` library.
3) Later, add a higher-perf adapter:
   - `libs/adapters/dx_capture/dxcam.py` (DXGI duplication).
4) Agent publishes a rolling `fps` field in telemetry; TUI displays it (already wired).

## Port API (minimal)
Keep the interface technology-agnostic and small:

~~~python
# libs/ports/vision.py (excerpt — interface sketch)
from typing import Protocol, Optional, Tuple

class CapturePort(Protocol):
    def open(self, target: Optional[str] = None) -> None: ...
    def grab(self) -> "Frame": ...              # full frame
    def grab_roi(self, roi: Tuple[int,int,int,int]) -> "Frame": ...  # x,y,w,h
    def fps(self) -> float: ...
    def close(self) -> None: ...
~~~

This aligns with the ports/adapters boundary from ADR-0001.

## Adapter(s)
- **MSS (first)**: `libs/adapters/dx_capture/mss.py`  
  Rationale: straightforward, minimal deps, works on Windows VMs; good for bring-up.
- **DXCAM (later)**: `libs/adapters/dx_capture/dxcam.py`  
  Rationale: lower latency & higher throughput when we need it.

## Agent wiring
In `apps/agent/compose.py` or `service.py`, instantiate the adapter from config and compute a rolling FPS over recent grabs. Add `fps` to the heartbeat/state telemetry payload (wire spec already supports additional fields).

Telemetry example (no schema change required):
~~~json
{
  "api": "v1",
  "agent_id": "vm1",
  "state": "RUN",
  "fps": 12.4,
  "ts": 1737970042.12
}
~~~

## Configuration
Extend profile TOMLs per ADR-0003. Example:

~~~toml
# configs/profiles/vm1.toml
[agent.capture]
adapter = "mss"            # "mss" now; "dxcam" later
monitor = 1                # or window_title = "EverQuest"
target_fps = 10.0          # advisory; adapter may throttle accordingly
roi_profile = "1600x900"   # optional: maps to configs/rois/1600x900.toml
~~~

## Tests (per ADR-0004)
- **Contract tests** (`@pytest.mark.contract`):
  - `grab()` returns a frame-like object; dims non-zero.
  - `grab_roi(roi)` returns expected dims.
  - `fps()` increases above zero when grabbing in a loop.
- **Unit tests**: ROI math independent of hardware; load `configs/rois/1600x900.toml`.
- **E2E smoke (optional later)**: agent + coordinator run; FPS arrives within N seconds.

## Performance & SLAs (initial)
- **MSS baseline**: 5–20 FPS at 1600×900 expected on VM; acceptable for bring-up.
- **DXCAM target (later)**: 30–60+ FPS on modest hardware when needed.

## Consequences
- :white_check_mark: Fast path to live pixels + FPS, minimal risk.
- :white_check_mark: Clear upgrade path for performance.
- :heavy_minus_sign: MSS may be slower; acceptable for initial milestones.

## Alternatives Considered
- Start with DXGI first: higher perf, but more initial friction.
- Window-capture-only first: simpler, but we want flexibility for multi-monitor.

## Rollout Plan
1. Land `mss` adapter and config plumbing.
2. Publish `fps` via telemetry; verify TUI shows values.
3. Add contract tests; gate in CI (Windows).
4. Later: add `dxcam` adapter behind the same port/tests.
