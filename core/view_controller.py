import asyncio
from core import tl
from core import cookies_manager
from core import kick
from core import formatter


async def view_stream(username, category_id):
    cookies = cookies_manager.load_cookies("cookies.txt")
    token = kick.get_token_with_cookies(cookies)
    streamerid = kick.get_channel_id(username)
    status = await kick.connection_channel(streamerid, username, category_id, token)
    return status

async def check_campaigns_claim_status():
    cookies = cookies_manager.load_cookies("cookies.txt")
    kickdata = kick.get_drops_progress(cookies)
    formatter.sync_drops_data(kickdata, cookies)

async def sleeping_director_list(category_id, streamers):
    for username in streamers:
        print(tl.c["streamer_found"].format(username=username))
        status = await view_stream(username, category_id)
        if status == True:
            print(tl.c["streamer_play_another_game"].format(username=username))
            continue
        await asyncio.sleep(4)  # 2 секунды паузы

async def run_with_timer(coro_func, timeout_seconds: int):
    task_main = asyncio.create_task(coro_func())
    task_timer = asyncio.create_task(asyncio.sleep(timeout_seconds))

    done, pending = await asyncio.wait(
        {task_main, task_timer},
        return_when=asyncio.FIRST_COMPLETED
    )

    # Если сработал таймер
    if task_timer in done and not task_main.done():
        minutes = timeout_seconds // 60
        print(tl.c["timer_finished"].format(minutes=minutes))
        task_main.cancel()
        try:
            await task_main
        except asyncio.CancelledError:
            print(tl.c["timer_stop"])

    # Если основная задача закончилась раньше
    elif task_main in done and not task_timer.done():
        print(tl.c["timer_task_early"])
        task_timer.cancel()

    print(tl.c["all_tasks_completed"])

