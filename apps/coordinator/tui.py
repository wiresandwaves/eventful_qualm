from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast

from rich.text import Text
from shared.config.loader import load_coordinator_settings
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static

from apps.coordinator.compose import build_ipc


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# helper for safe dt age
def _age_seconds(ts: datetime | None) -> float | None:
    if not ts:
        return None
    return (datetime.now(UTC) - ts).total_seconds()


@dataclass
class AgentRow:
    name: str
    cmd_ep: str
    last_seen: str = "-"
    heartbeats: int = 0
    fps: float | None = None
    state: str = "-"
    last_seen_ts: datetime | None = None


class CoordinatorTUI(App):
    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "ping", "Ping"),
        ("h", "hold", "Hold"),
        ("r", "resume", "Resume"),
        ("R", "refresh", "Refresh"),
        ("s", "sort", "Sort"),
        ("?", "help", "Help"),
    ]

    # UI state
    rows: reactive[dict[str, AgentRow]] = reactive(dict)

    def __init__(self) -> None:
        super().__init__()
        # Load settings and build IPC
        self.settings = load_coordinator_settings()
        self.cmd_port, self.sub_port = build_ipc(self.settings)
        self._sub_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._table: DataTable | None = None
        self._status: Static | None = None
        self._last_msg_ts: datetime | None = None

        # UI knobs (non-breaking defaults if not present in settings)
        self._heartbeat_hz: float = getattr(self.settings, "heartbeat_hz", 1.0)
        ui = getattr(self.settings, "ui", SimpleNamespace())
        self._stale_factor: float = getattr(ui, "stale_factor", 2.0)
        self._ttl_factor: float = getattr(ui, "ttl_factor", 3.0)
        self._sort_mode: str = "last"  # last | agent | state

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(
            f"[b]ipc_impl[/b]= {self.settings.ipc_impl} • agents: {', '
                                                                    .join(self.settings.agents_cmd.keys())}"
        )
        table = DataTable(zebra_stripes=True)
        table.add_columns("Agent", "Last Seen (UTC)", "State", "Heartbeats", "FPS", "Endpoint")
        self._table = table
        # status bar under table (dynamic)
        self._status = Static("")
        yield table
        yield self._status
        yield Footer()

    def on_mount(self) -> None:
        # Seed rows from settings
        self.rows = {
            name: AgentRow(name=name, cmd_ep=ep) for name, ep in self.settings.agents_cmd.items()
        }
        self._refresh_table()

        # Start telemetry reader
        self._stop.clear()
        self._sub_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._sub_thread.start()

        # Give SUB a moment to connect initially
        time.sleep(0.1)

    def on_unmount(self) -> None:
        self._stop.set()
        if self._sub_thread and self._sub_thread.is_alive():
            self._sub_thread.join(timeout=1.0)

    # ----- Actions (key bindings) -----

    def action_quit(self) -> None:
        self.exit()

    def _selected_agent(self) -> AgentRow | None:
        if not self._table or not self.rows:
            return None
        row_idx = self._table.cursor_row
        # respect current visible ordering
        keys = [r.name for r in self._sorted_rows()]
        if 0 <= row_idx < len(keys):
            return cast(AgentRow, self.rows[keys[row_idx]])
        return None

    def action_refresh(self) -> None:
        self._refresh_table()

    def action_ping(self) -> None:
        self._send_command("PING")

    def action_hold(self) -> None:
        self._send_command("HOLD")

    def action_resume(self) -> None:
        self._send_command("RESUME")

    def action_sort(self) -> None:
        self._sort_mode = {"last": "agent", "agent": "state", "state": "last"}[self._sort_mode]
        self.notify(f"Sort: {self._sort_mode}", severity="information")
        self._refresh_table()

    def action_help(self) -> None:
        self.notify(
            "Keys: q quit • p ping • h hold • r resume • R refresh • s sort • ? help\n"
            "Sort cycles: last seen → agent → state\n"
            "Rows turn yellow when stale; red when no telemetry yet.",
            severity="information",
        )

    def _send_command(self, ctype: str) -> None:
        ag = self._selected_agent()
        if not ag:
            self.notify("No agent selected", severity="warning")
            return
        try:
            t0 = time.perf_counter()
            resp = self.cmd_port.send(ag.cmd_ep, SimpleNamespace(type=ctype))
            dt_ms = int((time.perf_counter() - t0) * 1000)
            ok = bool(resp.get("ok"))
            err_code = (resp.get("error") or {}).get("code", "timeout" if not ok else "")
            self.notify(
                f"{ctype} → {ag.name}: {'✓ ' + str(dt_ms) + 'ms' if ok else '✕ ' + err_code}",
                severity=("information" if ok else "error"),
            )
        except Exception as ex:
            self.notify(f"{ctype} failed: {ex!r}", severity="error")

    # ----- Telemetry loop -----

    def _telemetry_loop(self) -> None:
        # subscribe endpoints already connected in build_ipc; just read
        while not self._stop.is_set():
            try:
                msg = self.sub_port.recv(timeout_ms=250)
            except Exception:
                msg = None
            if not msg:
                continue

            topic = msg.get("topic")
            data = msg.get("data", {}) or {}
            agent_id = data.get("agent_id")  # tagged by agent now

            # choose which rows to update
            targets = []
            if agent_id and agent_id in self.rows:
                targets = [self.rows[agent_id]]
            else:
                # fallback: update all (e.g., older agents that didn't include agent_id)
                targets = list(self.rows.values())

            now_iso = _utc_now_iso()
            now_dt = datetime.now(UTC)
            for row in targets:
                row.last_seen = now_iso
                row.last_seen_ts = now_dt
                if topic == "heartbeat":
                    row.heartbeats += 1
                    # optional: reflect hold in state if provided
                    if "hold" in data:
                        row.state = "HOLD" if data.get("hold") else "RUN"
                elif topic == "state":
                    s = str(data.get("state") or "").upper()
                    if s:
                        row.state = s
                # fps metric (when published)
                if "fps" in data:
                    try:
                        row.fps = float(data["fps"])
                    except Exception:
                        pass

            self._last_msg_ts = now_dt
            self.call_from_thread(self._refresh_table)
        # end loop

    # ----- Table rendering -----

    def _refresh_table(self) -> None:
        if not self._table:
            return
        self._table.clear()
        for row in self._sorted_rows():
            status = self._classify(row)
            # state cell with color + stale/down hints
            if status == "DOWN":
                state_cell = Text("DOWN", style="red")
            elif status == "STALE":
                state_cell = Text((row.state or "-") + " (STALE)", style="yellow")
            else:
                state_cell = Text(
                    row.state or "-",
                    style="green" if (row.state or "").upper() in {"RUN", "OK"} else "",
                )

            self._table.add_row(
                row.name,
                row.last_seen,
                state_cell,
                str(row.heartbeats),
                f"{row.fps:.1f}" if row.fps is not None else "-",
                row.cmd_ep,
            )
        # update status bar
        if self._status:
            self._status.update(self._status_text())

    def _classify(self, row: AgentRow) -> str:
        """Return OK | STALE | DOWN based on last_seen_ts."""
        if not row.last_seen_ts:
            return "DOWN"
        age = _age_seconds(row.last_seen_ts) or 0.0
        stale_threshold = self._stale_factor * (1.0 / max(self._heartbeat_hz, 0.001))
        return "STALE" if age > stale_threshold else "OK"

    def _sorted_rows(self) -> list[AgentRow]:
        items = list(self.rows.values())
        if self._sort_mode == "agent":
            items.sort(key=lambda r: r.name.lower())
        elif self._sort_mode == "state":
            items.sort(key=lambda r: (r.state, r.name.lower()))
        else:  # "last"
            items.sort(key=lambda r: r.last_seen_ts or datetime.fromtimestamp(0, UTC), reverse=True)
        return items

    def _status_text(self) -> str:
        configured = len(self.rows)
        # "connected" = telemetry within ttl window
        ttl_secs = self._ttl_factor * (1.0 / max(self._heartbeat_hz, 0.001))
        now = datetime.now(UTC)
        connected = sum(
            1
            for r in self.rows.values()
            if (r.last_seen_ts and (now - r.last_seen_ts) <= timedelta(seconds=ttl_secs))
        )
        last_ts = self._last_msg_ts.isoformat(timespec="seconds") if self._last_msg_ts else "—"
        return (
            f"Agents: {connected}/{configured} • Last msg: {last_ts}"
            + f" • Sort: {self._sort_mode} • Q quit  ? help"
        )
