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
        yield Static("WS: disconnected", id="streamer-ws")

    def watch_username(self, name: str) -> None:
        self.query_one("#streamer-name", Static).update(name)

    def watch_is_live(self, live: bool) -> None:
        status = "● LIVE" if live else "○ OFFLINE"
        self.query_one("#streamer-status", Static).update(status)

    def watch_game_name(self, game: str) -> None:
        self.query_one("#streamer-game", Static).update(f"🎮 {game}")

    def watch_ws_state(self, state: str) -> None:
        ws = self.query_one("#streamer-ws", Static)
        ws.update(f"WS: {state}  ❤ {self.heartbeat_count}")

    def watch_heartbeat_count(self, count: int) -> None:
        ws = self.query_one("#streamer-ws", Static)
        ws.update(f"WS: {self.ws_state}  ❤ {count}")


class ProgressPanel(Container):
    """Drop progress: per-streamer progress bars, claimed/pending/ready counts."""

    progress_text: reactive[str] = reactive("No progress data")
    claimed_count: reactive[int] = reactive(0)
    pending_count: reactive[int] = reactive(0)
    ready_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Label("DROP PROGRESS", classes="panel-title")
        yield Static("No progress data", id="progress-bar")
        yield Static("✓ claimed: 0  ⏳ pending: 0  🎁 ready: 0", id="progress-counts")

    def watch_progress_text(self, text: str) -> None:
        self.query_one("#progress-bar", Static).update(text)

    def watch_claimed_count(self, _count: int) -> None:
        self._update_counts()

    def watch_pending_count(self, _count: int) -> None:
        self._update_counts()

    def watch_ready_count(self, _count: int) -> None:
        self._update_counts()

    def _update_counts(self) -> None:
        self.query_one("#progress-counts", Static).update(
            f"✓ claimed: {self.claimed_count}  "
            f"⏳ pending: {self.pending_count}  "
            f"🎁 ready: {self.ready_count}"
        )

    def render_progress_bar(self, remaining_minutes: float, total_minutes: float) -> str:
        """Render an ASCII progress bar."""
        if total_minutes <= 0:
            return "complete"
        pct = max(0.0, min(1.0, 1.0 - (remaining_minutes / total_minutes)))
        bar_width = 20
        filled = int(bar_width * pct)
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty
        return f"{bar} {int(pct * 100)}%  {int(remaining_minutes)}m remaining"


class EventLog(RichLog):
    """Scrollable event log wrapping Textual's RichLog with color-coding."""

    def __init__(self) -> None:
        super().__init__(highlight=True, markup=True, max_lines=100)

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
