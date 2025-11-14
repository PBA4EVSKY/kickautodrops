import asyncio
import traceback
import os
from core import tl
from core import kick
from core import view_controller
from core import formatter
from functools import partial

async def create_file_tasks():
    listcamp = kick.get_all_campaigns()
    formatter.convert_drops_json(listcamp)

async def start_general_drops():
    while True:
        print(f"\n{tl.c['search_streamers']}")
        
        try:
            # Получаем случайного стримера из категории
            rndstreamercategory = kick.get_random_stream_from_category(13)
            
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
            
            # Проверяем категорию игры
            if stream_info['game_id'] != 13:
                print(tl.c["streamer_play_another_game"].format(username=username))
                await asyncio.sleep(30)
                continue

            print(tl.c["streamer_online"].format(username=username))
            print(tl.c["starting_view_streamer"].format(remaining=remaining))
            
            # Запускаем просмотр стрима
            stream_ended = await view_controller.run_with_timer(
                partial(view_controller.view_stream, username, 13), 
                remaining+120
            )
            
            # Если стрим закончился или сменилась игра
            if stream_ended:
                print(tl.c["streamer_play_another_game"].format(username=username))
                print(f"\n{tl.c['wait_for_new_streamer']}")
                await asyncio.sleep(60)
            else:
                # Стрим завершился нормально (по таймеру)
                print(tl.c["finish_view"].format(username=username))
                print(f"\n{tl.c['waitcd300seconds']}")
                await asyncio.sleep(300)
                
        except Exception as e:
            print(tl.c["error_viewing"].format(e=e))
            print(f"\n{tl.c['waitcd120seconds']}")
            await asyncio.sleep(120)

async def start_streamer_drops():
    while True:
        streamers_data = formatter.collect_usernames()
        found_online = False
        stream_ended = False
        print(f"\n{tl.c['search_streamers']}")
        
        for streamer in streamers_data:
            username = streamer['username']
            required_seconds = streamer['required_seconds']
            
            # Проверяем, осталось ли время для просмотра
            remaining = await formatter.get_remaining_time(username)
            if remaining <= 0:
                print(tl.c["streamer_time_skip"].format(username=username))
                continue
            
            stream_info = await kick.get_stream_info(username)
            
            if stream_info['is_live'] and stream_info['game_id'] == 13:
                    print(tl.c["streamer_found"].format(username=username))
                    print(tl.c["starting_view_streamer"].format(remaining=remaining))
                        # Запускаем фарм для этого стримера
                    found_online = True
                    # fuck this fix
                    stream_ended = await view_controller.run_with_timer(
                        partial(view_controller.view_stream, username, 13), 
                        required_seconds+120
                    )
                    
                    
                    # Если стример закончил или сменил игру
                    if stream_ended:
                        print(tl.c["streamer_play_another_game"].format(username=username))
                        print(f"\n{tl.c['waitcd120seconds']}")
                        await asyncio.sleep(120)
                        break  # Выходим из цикла for, чтобы начать новый поиск
                    else:
                        # Стрим завершился нормально (по таймеру)
                        print(tl.c['finish_view'].format(username=username))
                        # Проверяем оставшееся время
                        remaining_after = await formatter.get_remaining_time(username)
                        print(remaining_after)
                        if remaining_after > 0:
                            print(f"\n{tl.c['waitcd120seconds']}")
                            await asyncio.sleep(120)
                            break  # Ищем следующего онлайн стримера
                        else:
                            print(tl.c['finish_view'].format(username=username))
                            await asyncio.sleep(60)
                            break
            else:
                print(tl.c["streamer_offline"].format(username=username))
        
        # Если никто не онлайн
        if not found_online:
            print(f"\n{tl.c['all_streamers_offline']}")
            print(f"\n{tl.c['wait_streamers_online']}")
            rndstreamercategory = kick.get_random_stream_from_category(13)
            stream_ended = await view_controller.run_with_timer(
                    partial(view_controller.view_stream, rndstreamercategory['username'], 13), 
                    3600
                )
            await asyncio.sleep(600)



async def show_menu():
    print("Thanks Mixanicys")
    if not os.path.exists("current_views.json"):
        await create_file_tasks()
    else:
        print(tl.c['file_view_found'])
    
    menu_items = {
        "1": (tl.c['start_streamers_drops'], lambda: start_streamer_drops()),
        "2": (tl.c['start_general_drops'], lambda: start_general_drops()),
        "0": (tl.c['exit'], None)
    }

    while True:
        for key, (label, _) in menu_items.items():
            print(f"{key}. {label}")
        choice = input(tl.c['select_menu']).strip()

        if choice == "0":
            break

        action = menu_items.get(choice)
        
        if action is None:
            print(f"\n{tl.c['wrong_choice']}")
            input(tl.c['press_enter'])
            continue
        
        func = action[1]
        if func:
            print(f"\n{tl.c['launching']}: {action[0]}")
            await func()
        else:
            print(f"\n{tl.c['noaction']}")

if __name__ == "__main__":
    try:
        asyncio.run(show_menu())
    except KeyboardInterrupt:
        print(f"\n\n{tl.c['exit_script']}")
    except Exception as e:
        print(f"\n{tl.c['critical_error'].format(e=e)}")
        traceback.print_exc()