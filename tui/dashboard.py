"""Main dashboard screen composing all TUI widgets."""

from __future__ import annotations

import asyncio
import json
import os
import time
from functools import partial

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header

from core import cookies_manager, events, formatter, kick, tl, view_controller
from tui.widgets import EventLog, ModePanel, ProgressPanel, StreamerPanel


class DashboardScreen(Screen):
    """Main TUI dashboard for KickAutoDrops."""

    BINDINGS = [
        ("s", "start_stop", "Start/Stop"),
        ("p", "pause", "Pause"),
        ("m", "switch_mode", "Switch Mode"),
        ("n", "next_streamer", "Next Streamer"),
        ("c", "check_drops", "Check Drops"),
        ("q", "quit", "Exit"),
    ]

    farming: bool = False
    paused: bool = False
    start_time: float | None = None
    farm_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-panels"):
            yield ModePanel(id="mode-panel")
            yield StreamerPanel(id="streamer-panel")
            yield ProgressPanel(id="progress-panel")
        yield EventLog(id="event-log")
        yield Footer()

    def on_mount(self) -> None:
        """Subscribe to event bus and start background tasks when screen mounts."""
        self._refresh_progress()
        events.subscribe(self._on_event)
        self.set_interval(1, self._update_elapsed)

    def on_unmount(self) -> None:
        """Unsubscribe when screen unmounts."""
        events.unsubscribe(self._on_event)

    async def _on_event(self, event: events.Event) -> None:
        """Handle events from the core modules."""
        log = self.query_one("#event-log", EventLog)
        log.add_event(event.type.name, event.message)

        # Route specific events to panels
        streamer = self.query_one("#streamer-panel", StreamerPanel)

        if event.data:
            if event.data.get("heartbeat"):
                streamer.heartbeat_count += 1
            if event.data.get("category_changed"):
                streamer.is_live = False
            if event.data.get("streamer_offline"):
                streamer.is_live = False
                streamer.ws_state = "disconnected"

        if event.type in (events.EventType.PROGRESS, events.EventType.DROP_STATUS):
            self._refresh_progress()

    def _refresh_progress(self) -> None:
        """Reload progress from current_views.json and update panel."""
        if not os.path.exists("current_views.json"):
            return
        progress = self.query_one("#progress-panel", ProgressPanel)
        try:
            with open("current_views.json", "r") as f:
                data = json.load(f)
            planned = data.get("data", {}).get("planned", [])
            claimed = sum(1 for item in planned if item.get("claim") == 1)
            pending = sum(1 for item in planned if item.get("claim") == 0)
            progress.claimed_count = claimed
            progress.pending_count = pending
            progress.ready_count = 0

            # Build progress bar for first active streamer
            for item in planned:
                if item.get("claim") == 0:
                    remaining = item.get("required_units", 0)
                    if remaining > 0:
                        # Estimate total from remaining (imperfect but usable)
                        total = remaining * 1.25  # rough estimate
                        progress.progress_text = progress.render_progress_bar(remaining, total)
                        break
        except Exception:
            pass

    def _update_elapsed(self) -> None:
        """Update the elapsed timer in the header."""
        if self.farming and not self.paused and self.start_time:
            elapsed = int(time.time() - self.start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.query_one(Header).sub_title = f"⏱ {h:02d}:{m:02d}:{s:02d}"

    # -- Key bindings ------------------------------------------

    def action_start_stop(self) -> None:
        """Toggle farming on/off."""
        if self.farming and not self.paused:
            self._stop_farming()
        else:
            self._start_farming()

    def action_pause(self) -> None:
        """Pause or resume farming."""
        if not self.farming:
            return
        if self.paused:
            self.paused = False
            self._start_farming()
            events.emit(events.EventType.INFO, "▶ Resumed")
        else:
            self.paused = True
            self._stop_farming()
            events.emit(events.EventType.INFO, "⏸ Paused — press S to resume")

    def action_switch_mode(self) -> None:
        """Toggle between streamer and general drops."""
        if self.farming:
            self._stop_farming()
        mode_panel = self.query_one("#mode-panel", ModePanel)
        new_mode = mode_panel.toggle()
        self._refresh_progress()
        mode_name = "Streamer Drops" if new_mode == "streamer" else "General Drops"
        events.emit(events.EventType.INFO, f"Mode switched to: {mode_name}")

    def action_next_streamer(self) -> None:
        """Move to the next streamer in the campaign list."""
        if self.farming:
            self._stop_farming()
        events.emit(events.EventType.INFO, "Moving to next streamer...")
        # Will pick up next streamer on restart
        self._start_farming()

    def action_check_drops(self) -> None:
        """Force a drop progress check and auto-claim."""
        events.emit(events.EventType.INFO, "Checking drops...")
        self._check_drops_worker()

    @work(exclusive=False)
    async def _check_drops_worker(self) -> None:
        try:
            await view_controller.check_campaigns_claim_status()
            self._refresh_progress()
        except Exception as e:
            events.emit(events.EventType.ERROR, f"Failed to check drops: {e}")

    def action_quit(self) -> None:
        """Exit the application."""
        if self.farming:
            self._stop_farming()
        self.app.exit()

    # -- Farming lifecycle -------------------------------------

    def _start_farming(self) -> None:
        """Begin or resume farming."""
        self.farming = True
        self.paused = False
        if self.start_time is None:
            self.start_time = time.time()
        mode_panel = self.query_one("#mode-panel", ModePanel)
        streamer = self.query_one("#streamer-panel", StreamerPanel)
        streamer.ws_state = "connecting"

        if mode_panel.current_mode == "streamer":
            self.farm_task = asyncio.create_task(self._farm_streamer())
        else:
            self.farm_task = asyncio.create_task(self._farm_general())

    def _stop_farming(self) -> None:
        """Stop farming and disconnect."""
        if self.farm_task and not self.farm_task.done():
            self.farm_task.cancel()
        self.farming = False
        try:
            streamer = self.query_one("#streamer-panel", StreamerPanel)
            streamer.ws_state = "disconnected"
        except Exception:
            pass

    async def _farm_streamer(self) -> None:
        """Run streamer-specific drops loop."""
        streamer_panel = self.query_one("#streamer-panel", StreamerPanel)

        while self.farming and not self.paused:
            streamers_data = formatter.collect_usernames()
            found_online = False

            for streamer_data in streamers_data:
                if not self.farming or self.paused:
                    break

                username = streamer_data.get("username", "")
                required_seconds = streamer_data.get("required_seconds", 0)
                claim_status = streamer_data.get("claim", 0)

                if claim_status == 1:
                    events.emit(events.EventType.INFO, tl.c["streamer_time_skip"].format(username=username))
                    continue

                remaining = await formatter.get_remaining_time(username)
                if remaining <= 0:
                    events.emit(events.EventType.INFO, tl.c["streamer_time_skip"].format(username=username))
                    continue

                stream_info = await kick.get_stream_info(username)
                if stream_info.get("is_live") and stream_info.get("game_id") == 13:
                    found_online = True
                    streamer_panel.username = username
                    streamer_panel.is_live = True
                    streamer_panel.game_name = "Rust"
                    streamer_panel.ws_state = "connected"

                    stream_ended = await view_controller.run_with_timer(
                        partial(view_controller.view_stream, username, 13),
                        required_seconds + 120,
                    )

                    if not self.farming:
                        break

                    if stream_ended:
                        streamer_panel.is_live = False
                        streamer_panel.ws_state = "disconnected"
                        await asyncio.sleep(120)
                        break
                    else:
                        await view_controller.check_campaigns_claim_status()
                        self._refresh_progress()
                        await asyncio.sleep(60)
                        break
                else:
                    events.emit(events.EventType.WARNING, tl.c["streamer_offline"].format(username=username))

            if not self.farming:
                break

            if not found_online:
                events.emit(events.EventType.WARNING, tl.c["all_streamers_offline"])
                await view_controller.check_campaigns_claim_status()
                self._refresh_progress()
                await asyncio.sleep(600)

    async def _farm_general(self) -> None:
        """Run general drops loop."""
        streamer_panel = self.query_one("#streamer-panel", StreamerPanel)

        while self.farming and not self.paused:
            rnd = kick.get_random_stream_from_category(13)
            if not rnd or not rnd.get("username"):
                events.emit(events.EventType.WARNING, tl.c["unablefindstreamer"])
                await asyncio.sleep(300)
                continue

            username = rnd["username"]
            streamer_panel.username = username

            stream_info = await kick.get_stream_info(username)
            if not stream_info.get("is_live") or stream_info.get("game_id") != 13:
                events.emit(events.EventType.WARNING, tl.c["streamer_offline_looking_another"].format(username=username))
                await asyncio.sleep(30)
                continue

            streamer_panel.is_live = True
            streamer_panel.game_name = "Rust"
            streamer_panel.ws_state = "connected"

            remaining = await formatter.get_remaining_time(username)
            events.emit(events.EventType.INFO, tl.c["starting_view_streamer"].format(remaining=remaining))

            stream_ended = await view_controller.run_with_timer(
                partial(view_controller.view_stream, username, 13),
                remaining + 120,
            )

            if not self.farming:
                break

            if stream_ended:
                streamer_panel.is_live = False
                streamer_panel.ws_state = "disconnected"
                await view_controller.check_campaigns_claim_status()
                self._refresh_progress()
                await asyncio.sleep(60)
            else:
                events.emit(events.EventType.SUCCESS, tl.c["finish_view"].format(username=username))
                await view_controller.check_campaigns_claim_status()
                self._refresh_progress()
                await asyncio.sleep(300)
