"""Textual App subclass for KickAutoDrops TUI."""

from __future__ import annotations

from textual.app import App

from tui.dashboard import DashboardScreen


class KickAutoDropsApp(App):
    """Main Textual application for KickAutoDrops."""

    CSS = """
    #top-panels {
        height: 12;
        min-height: 10;
        max-height: 14;
    }

    #top-panels > Container {
        border: solid $accent;
        padding: 0 1;
        margin: 0 1;
    }

    .panel-title {
        text-style: bold;
        color: $text-muted;
        padding-bottom: 1;
    }

    #event-log {
        height: 1fr;
        border: solid $accent;
        margin: 1 1 1 1;
    }

    #mode-panel {
        width: 22;
    }

    #streamer-panel {
        width: 1fr;
    }

    #progress-panel {
        width: 40;
    }

    #streamer-name {
        text-style: bold;
        color: $text;
    }

    #streamer-status {
        color: $success;
    }

    #total-label, #current-label {
        text-style: bold;
        color: $text-muted;
    }

    #total-bar {
        color: $secondary;
    }

    #current-bar {
        color: $accent;
    }

    Footer {
        dock: bottom;
    }
    """

    TITLE = "\U0001f3ae KickAutoDrops"

    def on_mount(self) -> None:
        self.push_screen(DashboardScreen())
