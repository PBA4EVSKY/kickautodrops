import time
import asyncio
import random
import traceback
from core import formatter
from core import tl
from curl_cffi import requests, AsyncSession

DEFAULT_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://kick.com/',
    'Origin': 'https://kick.com',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}

async def view_random_stream_from_category(token, category_id: int):
    stream = get_random_stream_from_category(category_id)
    await connection_channel(stream['channel_id'], token, index=1)

def get_all_campaigns():
    headers = DEFAULT_HEADERS
    
    url = f'https://web.kick.com/api/v1/drops/campaigns'
    
    proxy = tl.get_proxy()
    response = requests.get(url, headers=headers, impersonate="chrome120", proxies=proxy)
    data = response.json()
    
    return data

def claim_drop_reward(reward_id, campaign_id, cookies, max_attempts=3):
    session_token = cookies.get('session_token')
    if not session_token:
        print(f"{tl.c['session_token_notfound_in_cookies']}")
        return None
    
    print(f"{tl.c['session_token_found']} {session_token[:30]}...")
    
    payload = {
        "reward_id": reward_id,
        "campaign_id": campaign_id
    }
    
    for attempt in range(max_attempts):
        proxy = tl.get_proxy()
        s = requests.Session(impersonate="chrome120", proxies=proxy)
        
        s.cookies.update(cookies)
        
        try:
            s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'ru-RU,ru;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Authorization': f'Bearer {session_token}',
                'X-Client-Token': 'e1393935a959b4020a4491574f6490129f678acdaa92760471263db43487f823',
                'Content-Type': 'application/json',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://kick.com/',
                'Origin': 'https://kick.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Sec-Ch-Ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Priority': 'u=1, i'
            })
            
            print(f"Attempting to claim reward {reward_id}... (attempt {attempt + 1}/{max_attempts})")
            response = s.post('https://web.kick.com/api/v1/drops/claim', json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('message') == 'Success':
                    print(f"✓ Reward claimed successfully! ID: {result.get('data', {}).get('id')}")
                    return result
                else:
                    print(f"⚠ Unexpected response: {result}")
                    return result
            else:
                print(f"✗ Error while claiming reward: {response.status_code}")
                print(f"Response: {response.text}")
                if attempt < max_attempts - 1:
                    print("Trying again...")
                    
        except Exception as e:
            print(f"✗ Error while claiming reward: {e}")
            if attempt < max_attempts - 1:
                print("Trying again...")
        finally:
            s.close()
    
    print("Failed to claim reward after all attempts")
    return None

def get_drops_progress(cookies, max_attempts=3):
    session_token = cookies.get('session_token')
    if not session_token:
        print(f"{tl.c['session_token_notfound_in_cookies']}")
        return None
    
    print(f"{tl.c['session_token_found']} {session_token[:30]}...")
    
    for attempt in range(max_attempts):
        proxy = tl.get_proxy()
        s = requests.Session(impersonate="chrome120", proxies=proxy)
        
        s.cookies.update(cookies)
        
        try:
            
            s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'ru-RU,ru;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Authorization': f'Bearer {session_token}',
                'X-Client-Token': 'e1393935a959b4020a4491574f6490129f678acdaa92760471263db43487f823',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://kick.com/',
                'Origin': 'https://kick.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Sec-Ch-Ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Priority': 'u=1, i'
            })
            
            response = s.get('https://web.kick.com/api/v1/drops/progress', timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"✗ Error while requesting: {response.status_code}")
                if attempt < max_attempts - 1:
                    print("Trying again...")
                    
        except Exception as e:
            print(f"✗ Error while requesting: {e}")
            if attempt < max_attempts - 1:
                print("Trying again...")
        finally:
            s.close()
    
    print("Failed to retrieve data after all attempts")
    return None

def get_random_stream_from_category(category_id: int, limit: int = 10) -> dict:
    headers = DEFAULT_HEADERS
    url = f'https://web.kick.com/api/v1/livestreams?limit={limit}&sort=viewer_count_desc&category_id={category_id}'
    
    proxy = tl.get_proxy()
    response = requests.get(url, headers=headers, impersonate="chrome120", proxies=proxy)
    data = response.json()
    
    result = {
        'username': None,
        'channel_id': None
    }
    
    if data and 'data' in data:
        livestreams = data['data'].get('livestreams', [])
        
        if livestreams and len(livestreams) > 0:
            max_index = min(4, len(livestreams) - 1)
            random_index = random.randint(1, max_index) if max_index >= 1 else 0
            
            random_stream = livestreams[random_index]
            channel = random_stream.get('channel', {})
            
            result['username'] = channel.get('username')
            result['channel_id'] = channel.get('id')
    
    return result

async def get_stream_info(username: str) -> dict:
    headers = DEFAULT_HEADERS
    
    url = f'https://kick.com/api/v2/channels/{username}/videos'
    
    result = {
        'is_live': False,
        'game_id': None,
        'game_name': None,
        'live_stream_id': None
    }
    
    proxy = tl.get_proxy()
    async with AsyncSession(impersonate="chrome120", proxies=proxy) as session:
        try:
            proxy = tl.get_proxy()
            response = await session.get(url, proxies=proxy, headers=headers)
            data = response.json()
            
            if data and len(data) > 0:
                first_stream = data[0]
                
                result['is_live'] = first_stream.get('is_live', False)
                result['live_stream_id'] = first_stream.get('id')
                
                categories = first_stream.get('categories', [])
                if categories and len(categories) > 0:
                    result['game_id'] = categories[0].get('id')
                    result['game_name'] = categories[0].get('name')
        except Exception as e:
            print(f"{tl.c['error_getting_stream_info'].format(e=e)}")
    
    return result

def get_channel_id(channel_name, cookies=None):
    max_attempts = 3
    for attempt in range(max_attempts):
        proxy = tl.get_proxy()
        s = requests.Session(impersonate="chrome120", proxies=proxy)
        
        if cookies:
            s.cookies.update(cookies)
            
        try:
            s.headers.update(DEFAULT_HEADERS)
            
            proxy = tl.get_proxy()
            r = s.get(f"https://kick.com/api/v2/channels/{channel_name}", proxies=proxy, timeout=10)
            
            if r.status_code == 200:
                channel_id = r.json().get("id")
                return channel_id
            else:
                print(f"⚠ Status {r.status_code}, returning {attempt + 1}/{max_attempts}")
                
        except Exception as e:
            print(f"❌ Error: {e}, returning {attempt + 1}/{max_attempts}")
        
        time.sleep(2)
    
    print(f"{tl.c['error_getting_id_streamer_id']}")
    return None

def get_token_with_cookies(cookies):
    max_attempts = 5
    
    session_token = cookies.get('session_token')
    if not session_token:
        print(f"{tl.c['session_token_notfound_in_cookies']}")
        return None
    
    print(f"{tl.c['session_token_found']} {session_token[:30]}...")
    
    for attempt in range(max_attempts):
        proxy = tl.get_proxy()
        s = requests.Session(impersonate="chrome120", proxies=proxy)
        
        s.cookies.update(cookies)
        
        try:
            print(f"\n[Returning {attempt + 1}/{max_attempts}] Request a token with cookies...")
            
            s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'ru-RU,ru;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Authorization': f'Bearer {session_token}',
                'X-Client-Token': 'e1393935a959b4020a4491574f6490129f678acdaa92760471263db43487f823',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://kick.com/',
                'Origin': 'https://kick.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Sec-Ch-Ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Priority': 'u=1, i'
            })
            
            proxy = tl.get_proxy()
            r = s.get('https://websockets.kick.com/viewer/v1/token', proxies=proxy, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                token = data.get("data", {}).get("token")
                if token:
                    print(f"{tl.c['token_received']}")
                    return token
                else:
                    print(f"{tl.c['token_notfound_in_reponse']}")
            else:
                print(f"Status: {r.status_code}")
                print(f"Answer: {r.text[:300]}")
                
        except requests.RequestException as e:
            print(f"{tl.c['error_getting_token'].format(e=e)}")
        except Exception as e:
            print(f"{tl.c['error_getting_token'].format(e=e)}")
            traceback.print_exc()
        
        if attempt < max_attempts - 1:
            wait = 3 + attempt
            print(f"{tl.c['retry_after'].format(wait=wait)}")
            time.sleep(wait)
    
    print(f"{tl.c['error_token_all_attempts']}")
    return None

async def connection_channel(channel_id, username, category, token):
    max_retries = 10
    retry_count = 0
    current_info = await get_stream_info(username)

    watch_start_time = time.time()
    last_report_time = watch_start_time

    while retry_count < max_retries:
        try:
            print(f"{tl.c['websocket_connect']}")
            if current_info['is_live'] == False:
                print(f"{tl.c['streamer_offline'].format(username=username)}")
                category_changed = True
                break
            proxy = tl.get_proxy()
            async with AsyncSession(proxies=proxy, impersonate="chrome120", verify=False) as session:
                headers = DEFAULT_HEADERS
                
                ws = await session.ws_connect(
                    f"wss://websockets.kick.com/viewer/v1/connect?token={token}",
                    headers=headers
                )
                
                print(f"{tl.c['connection_successful']}")
                retry_count = 0
                
                counter = 0
                category_changed = False
                while True:
                    counter += 1
                    
                    try:
                        if counter % 2 == 0:
                            await ws.send_json({"type": "ping"})
                            print(f"📤 ping")
                        else:
                            await ws.send_json({
                                "type": "channel_handshake",
                                "data": {"message": {"channelId": channel_id}}
                            })
                            print(f"🤝 handshake (channel {channel_id})")
                        
                        
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            print(f"📥 Received: {response[:100]}...")
                        except asyncio.TimeoutError:
                            pass
                        
                        delay = 11 + random.randint(2, 7)
                        print(f"⏳ Delay {delay}с")
                        rndgamecheck = random.randint(1,3)
                        now = time.time()
                        delta = now - last_report_time

                        if delta >= 60:
                            if current_info.get('live_stream_id'):
                                await ws.send_json({
                                    "type": "user_event",
                                    "data": {
                                        "message": {
                                            "name": "tracking.user.watch.livestream",
                                            "channel_id": channel_id,
                                            "livestream_id": current_info['live_stream_id']
                                        }
                                    }
                                })
                            formatter.update_streamer_progress(username, 60)
                            last_report_time = now
                        if rndgamecheck == 2:
                            try:
                                current_info = await get_stream_info(username)
                                if current_info['game_id'] is not None:
                                    if category != current_info['game_id']:
                                        print(f"{tl.c['streamer_play_another_game'].format(username=username)}")
                                        formatter.update_streamer_progress(username, 60)
                                        last_report_time = now
                                        category_changed = True
                                        break
                                    if current_info['is_live'] == False:
                                        print(f"{tl.c['streamer_offline'].format(username=username)}")
                                        formatter.update_streamer_progress(username, 60)
                                        last_report_time = now
                                        category_changed = True
                                        break
                                    else:
                                        print(f"{tl.c['streamer_online'].format(username=username)}")
                            except Exception as check_error:
                                print(f"{tl.c['error_check_category'].format(check_error=check_error)}")
                        await asyncio.sleep(delay)
                        
                    except Exception as send_error:
                        print(f"{tl.c['error_send'].format(send_error=send_error)}")
                        break
                if category_changed:
                    return category_changed  
        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            print(f"\n ❌ Connection error (attempt {retry_count}/{max_retries})")
            print(f" Детали: {error_msg}")
            traceback.print_exc()
            if "403" in error_msg or "Refused" in error_msg:
                print(f"{tl.c['need_update_cookies']}")
                break
            
            if retry_count < max_retries:
                wait = random.randint(5, 10)
                print(f"{tl.c['retry_after'].format(wait=wait)}")
                await asyncio.sleep(wait)
            else:
                print(f"{tl.c['max_attemtps']}")
                break