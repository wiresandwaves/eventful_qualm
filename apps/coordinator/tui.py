from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

from shared.config.loader import load_coordinator_settings
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static

from apps.coordinator.compose import build_ipc


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class AgentRow:
    name: str
    cmd_ep: str
    last_seen: str = "-"
    heartbeats: int = 0
    fps: float | None = None
    state: str = "-"


class CoordinatorTUI(App):
    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "ping", "Ping"),
        ("h", "hold", "Hold"),
        ("r", "resume", "Resume"),
        ("R", "refresh", "Refresh"),
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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(
            f"[b]ipc_impl[/b]= {self.settings.ipc_impl} • agents: {', '
                                                                    .join(self.settings.agents_cmd.keys())}"
        )
        table = DataTable(zebra_stripes=True)
        table.add_columns("Agent", "Last Seen (UTC)", "State", "Heartbeats", "FPS", "Endpoint")
        self._table = table
        yield table
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
        keys = list(self.rows.keys())
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

    def _send_command(self, ctype: str) -> None:
        ag = self._selected_agent()
        if not ag:
            self.notify("No agent selected", severity="warning")
            return
        try:
            resp = self.cmd_port.send(ag.cmd_ep, SimpleNamespace(type=ctype))
            ok = resp.get("ok")
            self.notify(
                f"{ctype} → {ag.name}: {'OK' if ok else 'ERR'}",
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

            now = _utc_now_iso()
            for row in targets:
                row.last_seen = now
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

            self.call_from_thread(self._refresh_table)
        # end loop

    # ----- Table rendering -----

    def _refresh_table(self) -> None:
        if not self._table:
            return
        self._table.clear()
        for row in self.rows.values():
            self._table.add_row(
                row.name,
                row.last_seen,
                row.state or "-",
                str(row.heartbeats),
                f"{row.fps:.1f}" if row.fps is not None else "-",
                row.cmd_ep,
            )
