"""Custom Textual widgets for the KickAutoDrops TUI dashboard."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, Label, RichLog
from textual.reactive import reactive


class ModePanel(Container):
    """Radio-style mode selector showing Streamer Drops vs General Drops."""

    current_mode: reactive[str] = reactive("streamer")

    def compose(self) -> ComposeResult:
        yield Label("MODE", classes="panel-title")
        yield Static("● Streamer Drops", id="mode-streamer")
        yield Static("○ General Drops", id="mode-general")

    def watch_current_mode(self, mode: str) -> None:
        streamer = self.query_one("#mode-streamer", Static)
        general = self.query_one("#mode-general", Static)
        if mode == "streamer":
            streamer.update("● Streamer Drops")
            general.update("○ General Drops")
        else:
            streamer.update("○ Streamer Drops")
            general.update("● General Drops")

    def toggle(self) -> str:
        self.current_mode = "general" if self.current_mode == "streamer" else "streamer"
        return self.current_mode


class StreamerPanel(Container):
    """Shows active streamer: name, live status, game, WS state, heartbeat count."""

    username: reactive[str] = reactive("—")
    is_live: reactive[bool] = reactive(False)
    game_name: reactive[str] = reactive("—")
    ws_state: reactive[str] = reactive("disconnected")
    heartbeat_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Label("ACTIVE STREAMER", classes="panel-title")
        yield Static("—", id="streamer-name")
        yield Static("○ OFFLINE", id="streamer-status")
        yield Static("🎮 —", id="streamer-game")
        yield Static("⚡disconnected ♡0", id="streamer-ws")

    def watch_username(self, name: str) -> None:
        self.query_one("#streamer-name", Static).update(name)

    def watch_is_live(self, live: bool) -> None:
        status = "● LIVE" if live else "○ OFFLINE"
        self.query_one("#streamer-status", Static).update(status)

    def watch_game_name(self, game: str) -> None:
        self.query_one("#streamer-game", Static).update(f"🎮 {game}")

    def watch_ws_state(self, state: str) -> None:
        ws = self.query_one("#streamer-ws", Static)
        ws.update(f"⚡{state} ♡{self.heartbeat_count}")

    def watch_heartbeat_count(self, count: int) -> None:
        ws = self.query_one("#streamer-ws", Static)
        ws.update(f"⚡{self.ws_state} ♡{count}")


def _render_bar(pct: float, width: int = 20) -> str:
    """Render a fixed-width ASCII progress bar for a 0..1 fraction."""
    pct = max(0.0, min(1.0, pct))
    filled = int(width * pct)
    return "█" * filled + "░" * (width - filled)


def _format_eta(remaining_minutes: float) -> str:
    """Format a minutes value as a compact h/m ETA string."""
    total = max(0, int(round(remaining_minutes)))
    if total <= 0:
        return "0m"
    h, m = divmod(total, 60)
    if h and m:
        return f"{h}h {m:02d}m"
    if h:
        return f"{h}h"
    return f"{m}m"


class ProgressPanel(Container):
    """Drop progress split into two blocks: total across all drops, and the
    current drop being farmed.  Each block shows a bar and an ETA."""

    # -- Total (all planned drops) --
    total_drops: reactive[int] = reactive(0)
    claimed_drops: reactive[int] = reactive(0)
    total_eta_minutes: reactive[float] = reactive(0.0)

    # -- Current drop --
    current_label: reactive[str] = reactive("—")
    current_remaining: reactive[float] = reactive(0.0)
    current_total: reactive[float] = reactive(0.0)
    has_current: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Label("DROP PROGRESS", classes="panel-title")
        yield Static("", id="total-label")
        yield Static("", id="total-bar")
        yield Static("", id="current-label")
        yield Static("", id="current-bar")

    def on_mount(self) -> None:
        self._render_total()
        self._render_current()

    # -- Total block ------------------------------------------------
    def watch_total_drops(self, _v: int) -> None:
        self._render_total()

    def watch_claimed_drops(self, _v: int) -> None:
        self._render_total()

    def watch_total_eta_minutes(self, _v: float) -> None:
        self._render_total()

    def _render_total(self) -> None:
        try:
            label = self.query_one("#total-label", Static)
            bar = self.query_one("#total-bar", Static)
        except Exception:
            return
        total = self.total_drops
        claimed = self.claimed_drops
        pct = (claimed / total) if total > 0 else 0.0
        label.update(f"TOTAL  {claimed}/{total} claimed")
        bar.update(f"{_render_bar(pct)}  ⏳ {_format_eta(self.total_eta_minutes)} left")

    # -- Current block ----------------------------------------------
    def watch_current_label(self, _v: str) -> None:
        self._render_current()

    def watch_current_remaining(self, _v: float) -> None:
        self._render_current()

    def watch_current_total(self, _v: float) -> None:
        self._render_current()

    def watch_has_current(self, _v: bool) -> None:
        self._render_current()

    def _render_current(self) -> None:
        try:
            label = self.query_one("#current-label", Static)
            bar = self.query_one("#current-bar", Static)
        except Exception:
            return
        if not self.has_current:
            label.update("CURRENT  —")
            bar.update(f"{_render_bar(0.0)}  idle")
            return
        total = self.current_total
        remaining = self.current_remaining
        pct = (1.0 - remaining / total) if total > 0 else 1.0
        label.update(f"CURRENT  {self.current_label}")
        bar.update(
            f"{_render_bar(pct)}  {int(max(0.0, min(1.0, pct)) * 100)}%  "
            f"⏳ {_format_eta(remaining)} left"
        )


class EventLog(RichLog):
    """Scrollable event log wrapping Textual's RichLog with color-coding."""

    def __init__(self, **kwargs) -> None:
        super().__init__(highlight=True, markup=True, max_lines=100, **kwargs)

    def add_event(self, event_type_str: str, message: str) -> None:
        """Add a color-coded event to the log."""
        from datetime import datetime

        ts = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "SUCCESS": "green",
            "ERROR": "red",
            "WARNING": "yellow",
            "CONNECTION": "blue",
            "PROGRESS": "cyan",
            "DROP_STATUS": "magenta",
            "INFO": "white",
        }
        color = color_map.get(event_type_str, "white")
        self.write(f"[{color}]{ts}  {message}[/{color}]")
