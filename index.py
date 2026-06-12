#!/usr/bin/env python3
"""KickAutoDrops — Kick.com drop farming automation.

Usage:
    python index.py           # Launch TUI dashboard (default)
    python index.py --no-tui  # Launch headless CLI (original behavior)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import traceback
from functools import partial

from core import cookies_manager, formatter, kick, tl, view_controller
from core import events


# ── Headless event subscriber ──────────────────────────────────

async def _headless_event_handler(event: events.Event) -> None:
    """Print events to stdout in headless mode."""
    prefix_map = {
        events.EventType.SUCCESS: "✓",
        events.EventType.ERROR: "✗",
        events.EventType.WARNING: "⚠",
        events.EventType.INFO: "",
        events.EventType.CONNECTION: "\U0001f50c",
        events.EventType.PROGRESS: "\U0001f4be",
        events.EventType.DROP_STATUS: "\U0001f381",
    }
    prefix = prefix_map.get(event.type, "")
    print(f"{prefix} {event.message}")


# ── Headless mode (original CLI behavior) ──────────────────────

async def create_file_tasks():
    listcamp = kick.get_all_campaigns()
    formatter.convert_drops_json(listcamp)


async def start_general_drops():
    while True:
        events.emit(events.EventType.INFO, tl.c["search_streamers"])

        try:
            rndstreamercategory = kick.get_random_stream_from_category(13)

            if not rndstreamercategory:
                events.emit(events.EventType.WARNING, tl.c["unablefindstreamer"])
                events.emit(events.EventType.INFO, tl.c["waitcd300seconds"])
                await asyncio.sleep(300)
                continue

            username = rndstreamercategory["username"]
            remaining = await formatter.get_remaining_time(username)
            events.emit(events.EventType.SUCCESS, tl.c["streamer_found"].format(username=username))
            stream_info = await kick.get_stream_info(username)

            if not stream_info["is_live"]:
                events.emit(events.EventType.WARNING, tl.c["streamer_offline_looking_another"].format(username=username))
                await asyncio.sleep(30)
                continue

            if stream_info["game_id"] != 13:
                events.emit(events.EventType.WARNING, tl.c["streamer_play_another_game"].format(username=username))
                await asyncio.sleep(30)
                continue

            events.emit(events.EventType.SUCCESS, tl.c["streamer_online"].format(username=username))
            events.emit(events.EventType.INFO, tl.c["starting_view_streamer"].format(remaining=remaining))

            stream_ended = await view_controller.run_with_timer(
                partial(view_controller.view_stream, username, 13),
                remaining + 120,
            )

            if stream_ended:
                events.emit(events.EventType.WARNING, tl.c["streamer_play_another_game"].format(username=username))
                events.emit(events.EventType.INFO, tl.c["wait_for_new_streamer"])
                await view_controller.check_campaigns_claim_status()
                await asyncio.sleep(60)
            else:
                events.emit(events.EventType.SUCCESS, tl.c["finish_view"].format(username=username))
                events.emit(events.EventType.INFO, tl.c["waitcd300seconds"])
                await view_controller.check_campaigns_claim_status()
                await asyncio.sleep(300)

        except Exception as e:
            events.emit(events.EventType.ERROR, tl.c["error_viewing"].format(e=e))
            events.emit(events.EventType.INFO, tl.c["waitcd120seconds"])
            await asyncio.sleep(120)


async def start_streamer_drops():
    while True:
        streamers_data = formatter.collect_usernames()
        found_online = False
        events.emit(events.EventType.INFO, tl.c["search_streamers"])

        for streamer in streamers_data:
            username = streamer["username"]
            required_seconds = streamer["required_seconds"]
            claim_status = streamer["claim"]

            if claim_status == 1:
                events.emit(events.EventType.INFO, tl.c["streamer_time_skip"].format(username=username))
                continue

            remaining = await formatter.get_remaining_time(username)
            if remaining <= 0:
                events.emit(events.EventType.INFO, tl.c["streamer_time_skip"].format(username=username))
                continue

            stream_info = await kick.get_stream_info(username)

            if stream_info["is_live"] and stream_info["game_id"] == 13:
                events.emit(events.EventType.SUCCESS, tl.c["streamer_found"].format(username=username))
                events.emit(events.EventType.INFO, tl.c["starting_view_streamer"].format(remaining=remaining))
                found_online = True
                stream_ended = await view_controller.run_with_timer(
                    partial(view_controller.view_stream, username, 13),
                    required_seconds + 120,
                )

                if stream_ended:
                    events.emit(events.EventType.WARNING, tl.c["streamer_play_another_game"].format(username=username))
                    events.emit(events.EventType.INFO, tl.c["waitcd120seconds"])
                    await asyncio.sleep(120)
                    break
                else:
                    events.emit(events.EventType.SUCCESS, tl.c["finish_view"].format(username=username))
                    await asyncio.sleep(60)
                    break
            else:
                events.emit(events.EventType.WARNING, tl.c["streamer_offline"].format(username=username))

        if not found_online:
            events.emit(events.EventType.WARNING, tl.c["all_streamers_offline"])
            events.emit(events.EventType.INFO, tl.c["wait_streamers_online"])
            await view_controller.check_campaigns_claim_status()
            rndstreamercategory = kick.get_random_stream_from_category(13)
            await view_controller.run_with_timer(
                partial(view_controller.view_stream, rndstreamercategory["username"], 13),
                3600,
            )
            await asyncio.sleep(600)


async def show_menu():
    events.emit(events.EventType.INFO, tl.c["links"])
    await asyncio.sleep(3)
    events.emit(events.EventType.INFO, "Thanks Mixanicys")
    if not os.path.exists("current_views.json"):
        await create_file_tasks()
    else:
        events.emit(events.EventType.INFO, tl.c["file_view_found"])

    await asyncio.sleep(3)
    await view_controller.check_campaigns_claim_status()

    menu_items = {
        "1": (tl.c["start_streamers_drops"], lambda: start_streamer_drops()),
        "2": (tl.c["start_general_drops"], lambda: start_general_drops()),
        "0": (tl.c["exit"], None),
    }

    while True:
        for key, (label, _) in menu_items.items():
            print(f"{key}. {label}")
        choice = input(tl.c["select_menu"]).strip()

        if choice == "0":
            break

        action = menu_items.get(choice)

        if action is None:
            print(f"\n{tl.c['wrong_choice']}")
            input(tl.c["press_enter"])
            continue

        func = action[1]
        if func:
            print(f"\n{tl.c['launching']}: {action[0]}")
            await func()
        else:
            print(f"\n{tl.c['noaction']}")


async def run_headless():
    """Run the original CLI (headless) experience."""
    events.subscribe(_headless_event_handler)
    try:
        await show_menu()
    except KeyboardInterrupt:
        print(f"\n\n{tl.c['exit_script']}")
    except Exception as e:
        print(f"\n{tl.c['critical_error'].format(e=e)}")
        traceback.print_exc()


# ── Entry point ────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KickAutoDrops")
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Run in headless CLI mode (no TUI dashboard)",
    )
    args = parser.parse_args()

    if args.no_tui:
        asyncio.run(run_headless())
    else:
        from tui.app import KickAutoDropsApp

        app = KickAutoDropsApp()
        app.run()
