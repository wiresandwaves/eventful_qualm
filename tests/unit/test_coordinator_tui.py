# tests/unit/test_coordinator_tui.py
from datetime import UTC, datetime, timedelta

from apps.coordinator.tui import AgentRow, CoordinatorTUI


def make_app():
    # Use the real constructor so Textual's Reactable init runs
    app = CoordinatorTUI()

    # Don't mutate pydantic settings. Just configure the internal knobs used by helpers.
    app._heartbeat_hz = 1.0  # 1 Hz heartbeat period
    app._stale_factor = 2.0  # STALE after 2 × period (2s at 1 Hz)
    app._ttl_factor = 3.0  # "connected" if seen within 3 × period (3s)
    app._sort_mode = "last"

    # We aren't rendering a UI here
    app._table = None
    app._status = None

    # Seed rows
    app.rows = {
        "vm1": AgentRow(name="vm1", cmd_ep="cmd://vm1"),
        "vm2": AgentRow(name="vm2", cmd_ep="cmd://vm2"),
    }
    return app


def test_classify_down_and_stale_and_ok():
    app = make_app()
    r = app.rows["vm1"]

    # DOWN: no telemetry yet
    assert app._classify(r) == "DOWN"

    # STALE: older than stale_factor * heartbeat period (2s @ 1 Hz)
    r.last_seen_ts = datetime.now(UTC) - timedelta(seconds=3.1)
    assert app._classify(r) == "STALE"

    # OK: recent
    r.last_seen_ts = datetime.now(UTC)
    assert app._classify(r) == "OK"


def test_sorted_rows_orders_by_last_seen_desc():
    app = make_app()
    now = datetime.now(UTC)
    app.rows["vm1"].last_seen_ts = now - timedelta(seconds=5)
    app.rows["vm2"].last_seen_ts = now - timedelta(seconds=1)

    app._sort_mode = "last"
    names = [r.name for r in app._sorted_rows()]
    assert names == ["vm2", "vm1"]


def test_sorted_rows_by_agent_and_state():
    app = make_app()
    app.rows["vm1"].state = "RUN"
    app.rows["vm2"].state = "HOLD"

    app._sort_mode = "agent"
    assert [r.name for r in app._sorted_rows()] == ["vm1", "vm2"]

    app._sort_mode = "state"
    assert [r.name for r in app._sorted_rows()] == ["vm2", "vm1"]  # HOLD < RUN


def test_status_text_connected_vs_configured_counts():
    app = make_app()
    now = datetime.now(UTC)
    # ttl = ttl_factor * 1/heartbeat_hz = 3s
    app.rows["vm1"].last_seen_ts = now - timedelta(seconds=1)  # connected
    app.rows["vm2"].last_seen_ts = now - timedelta(seconds=10)  # not connected
    app._last_msg_ts = now
    s = app._status_text()
    assert "Agents: 1/2" in s
    assert "Last msg:" in s
