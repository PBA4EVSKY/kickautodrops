import argparse
import asyncio
import traceback
import os
import time
from core import tl
from core import kick
from core import view_controller
from core import formatter
from core import cookies_manager
from functools import partial

# Log mode, can be set via UI toggle
LOG_MODE_DETAILED = False

def production_log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def debug_log(msg):
    if LOG_MODE_DETAILED:
        print(f"[DEBUG {time.strftime('%H:%M:%S')}] {msg}")

async def create_file_tasks():
    production_log("Initializing campaign info from Kick.")
    listcamp = kick.get_all_campaigns()
    formatter.convert_drops_json(listcamp)
    production_log("Campaign info loaded.")

async def start_streamer_drops(category_id):
    production_log(f"Beginning targeted farming for category {category_id}. By StuXan")
    while True:
        streamers_data = formatter.collect_usernames()
        debug_log(f"Loaded streamers_data: {streamers_data}")
        farmed_this_cycle = False
        for streamer in streamers_data:
            username = streamer['username']
            required_seconds = streamer['required_seconds']
            claim_status = streamer['claim']
            if claim_status == 1 or required_seconds == 0:
                debug_log(f"Skipping {username} (claimed or no time left).")
                continue
            debug_log(f"Getting stream info for {username}...")
            start_time = time.time()
            stream_info = await kick.get_stream_info(username)
            elapsed = time.time() - start_time
            if elapsed > 5:
                production_log(f"Stream info for {username} (took {elapsed:.1f}s): {stream_info}")
            else:
                debug_log(f"Stream info for {username}: {stream_info}")
            if stream_info['is_live'] and stream_info['game_id'] == category_id:
                production_log(f"Started farming: {username} ({required_seconds // 60} min left, live now).")
                await view_controller.run_with_timer(
                    partial(view_controller.view_stream, username, category_id),
                    required_seconds
                )
                farmed_this_cycle = True
                await view_controller.check_campaigns_claim_status()
                production_log(f"Finished farming: {username}. Syncing claim status.")
                break
            else:
                production_log(f"Streamer unavailable: {username} (offline or wrong category). Skipped.")
        if not farmed_this_cycle:
            production_log("No targeted streamers are eligible at this time. Waiting 2 minutes before retry.")
            await asyncio.sleep(120)

async def run_farming(drop_mode, category_id):
    production_log("By StuXan")
    production_log("Farming system started.")
    if not os.path.exists("current_views.json"):
        await create_file_tasks()
    production_log("Campaign sync complete.")
    await asyncio.sleep(0.5)
    production_log("Checking targeted drops...")
    await view_controller.check_campaigns_claim_status()
    production_log("Running farming main loop.")
    if drop_mode == "streamers":
        production_log("Targeted Streamers farming mode enabled.")
        await start_streamer_drops(category_id)
    elif drop_mode == "general":
        production_log("General farming mode enabled.")
        await start_general_drops(category_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--category', type=int, default=13, help="Kick.com category/game ID. Default 13 (Rust)")
    parser.add_argument('--mode', choices=["streamers", "general"], default="streamers",
                        help="Select drop mode: streamers or general")
    parser.add_argument('--logs', choices=["prod", "debug"], default="prod", help="Choose log verbosity: prod or debug")
    args = parser.parse_args()
    LOG_MODE_DETAILED = (args.logs == "debug")
    try:
        asyncio.run(run_farming(args.mode, args.category))
    except KeyboardInterrupt:
        production_log("Farming stopped by user.")
    except Exception as e:
        production_log(f"Critical error: {e}")
        traceback.print_exc()