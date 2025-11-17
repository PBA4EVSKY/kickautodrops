import argparse
import asyncio
import traceback
import os
from core import tl
from core import kick
from core import view_controller
from core import formatter
from core import cookies_manager
from functools import partial

async def create_file_tasks():
    listcamp = kick.get_all_campaigns()
    formatter.convert_drops_json(listcamp)

async def start_general_drops(category_id):
    while True:
        print(f"\n{tl.c['search_streamers']}")
        try:
            rndstreamercategory = kick.get_random_stream_from_category(category_id)
            if not rndstreamercategory:
                print(f"\n{tl.c['unablefindstreamer']}")
                print(f"\n{tl.c['waitcd300seconds']}")
                await asyncio.sleep(300)
                continue
            username = rndstreamercategory['username']
            remaining = await formatter.get_remaining_time(username)
            print(tl.c["streamer_found"].format(username=username))
            stream_info = await kick.get_stream_info(username)
            if not stream_info['is_live']:
                print(tl.c["streamer_offline_looking_another"].format(username=username))
                await asyncio.sleep(30)
                continue
            if stream_info['game_id'] != category_id:
                print(tl.c["streamer_play_another_game"].format(username=username))
                await asyncio.sleep(30)
                continue

            print(tl.c["streamer_online"].format(username=username))
            print(tl.c["starting_view_streamer"].format(remaining=remaining))
            stream_ended = await view_controller.run_with_timer(
                partial(view_controller.view_stream, username, category_id),
                remaining + 120
            )
            if stream_ended:
                print(tl.c["streamer_play_another_game"].format(username=username))
                print(f"\n{tl.c['wait_for_new_streamer']}")
                await view_controller.check_campaigns_claim_status()
                await asyncio.sleep(60)
            else:
                print(tl.c["finish_view"].format(username=username))
                print(f"\n{tl.c['waitcd300seconds']}")
                await view_controller.check_campaigns_claim_status()
                await asyncio.sleep(300)
        except Exception as e:
            print(tl.c["error_viewing"].format(e=e))
            print(f"\n{tl.c['waitcd120seconds']}")
            await asyncio.sleep(120)

async def start_streamer_drops(category_id):
    while True:
        streamers_data = formatter.collect_usernames()
        found_online = False
        stream_ended = False
        print(f"\n{tl.c['search_streamers']}")
        for streamer in streamers_data:
            username = streamer['username']
            required_seconds = streamer['required_seconds']
            claim_status = streamer['claim']
            if claim_status == 1:
                print(tl.c["streamer_time_skip"].format(username=username))
                continue
            remaining = await formatter.get_remaining_time(username)
            if remaining <= 0:
                print(tl.c["streamer_time_skip"].format(username=username))
                continue
            stream_info = await kick.get_stream_info(username)
            if stream_info['is_live'] and stream_info['game_id'] == category_id:
                print(tl.c["streamer_found"].format(username=username))
                print(tl.c["starting_view_streamer"].format(remaining=remaining))
                found_online = True
                stream_ended = await view_controller.run_with_timer(
                    partial(view_controller.view_stream, username, category_id),
                    required_seconds + 120
                )
                if stream_ended:
                    print(tl.c["streamer_play_another_game"].format(username=username))
                    print(f"\n{tl.c['waitcd120seconds']}")
                    await asyncio.sleep(120)
                    break
                else:
                    print(tl.c['finish_view'].format(username=username))
                    remaining_after = await formatter.get_remaining_time(username)
                    print(remaining_after)
                    if remaining_after > 0:
                        print(f"\n{tl.c['waitcd120seconds']}")
                        await asyncio.sleep(120)
                        break
                    else:
                        print(tl.c['finish_view'].format(username=username))
                        await asyncio.sleep(60)
                        break
            else:
                print(tl.c["streamer_offline"].format(username=username))
        if not found_online:
            print(f"\n{tl.c['all_streamers_offline']}")
            print(f"\n{tl.c['wait_streamers_online']}")
            await view_controller.check_campaigns_claim_status()
            rndstreamercategory = kick.get_random_stream_from_category(category_id)
            stream_ended = await view_controller.run_with_timer(
                partial(view_controller.view_stream, rndstreamercategory['username'], category_id),
                3600
            )
            await asyncio.sleep(600)

async def run_farming(drop_mode, category_id):
    print("Thanks Mixanicys")
    if not os.path.exists("current_views.json"):
        await create_file_tasks()
    else:
        print(tl.c['file_view_found'])
    await asyncio.sleep(3)
    await view_controller.check_campaigns_claim_status()
    if drop_mode == "streamers":
        print("\nLaunching: Streamers Drops mode")
        await start_streamer_drops(category_id)
    elif drop_mode == "general":
        print("\nLaunching: General Drops mode")
        await start_general_drops(category_id)
    else:
        print("\nUnknown drop mode requested:", drop_mode)
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--category', type=int, default=13, help="Kick.com category/game ID. Default 13 (Rust)")
    parser.add_argument('--mode', choices=["streamers", "general"], default="streamers",
                        help="Select drop mode: streamers or general")
    args = parser.parse_args()
    # Pass args.category where needed (see below)
    try:
        asyncio.run(run_farming(args.mode, args.category))
    except KeyboardInterrupt:
        print(f"\n\n{tl.c['exit_script']}")
    except Exception as e:
        print(f"\n{tl.c['critical_error'].format(e=e)}")
        traceback.print_exc()