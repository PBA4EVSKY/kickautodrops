import time
import asyncio
import random
import traceback
import threading
from typing import Optional
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

class ClaimManager:
    def __init__(self):
        self._reserved = set()
        self._claimed = set()
        self._lock = threading.Lock()
    def is_processed(self, reward_id):
        with self._lock:
            return reward_id in self._claimed
    def mark_claimed(self, reward_id, campaign_id):
        with self._lock:
            self._claimed.add(reward_id)
            self._reserved.discard(reward_id)
    def reserve(self, reward_id, campaign_id):
        with self._lock:
            if reward_id in self._claimed or reward_id in self._reserved:
                return False
            self._reserved.add(reward_id)
            return True
    def release_reservation(self, reward_id):
        with self._lock:
            self._reserved.discard(reward_id)

claim_manager = ClaimManager()

def get_proxy_or_none():
    proxy = tl.get_proxy()
    return proxy if proxy else None

def get_all_campaigns():
    headers = DEFAULT_HEADERS
    url = 'https://web.kick.com/api/v1/drops/campaigns'
    proxy = get_proxy_or_none()
    resp = requests.get(url, headers=headers, impersonate="chrome120", proxies=proxy)
    return resp.json()

def _is_reward_claimed_remote(cookies, reward_id, campaign_id, max_attempts=2):
    try:
        progress = get_drops_progress(cookies, max_attempts=max_attempts)
        if not progress:
            return None
        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ('id', 'reward_id') and str(v) == str(reward_id):
                        return obj
                    res = walk(v)
                    if res:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = walk(item)
                    if res:
                        return res
            return None
        found = walk(progress)
        if not found:
            def scan_list(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict) and str(item.get('id') or item.get('reward_id')) == str(reward_id):
                                    return item
                                res = scan_list(item)
                                if res:
                                    return res
                    for v in obj.values():
                        res = scan_list(v)
                        if res:
                            return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = scan_list(item)
                        if res:
                            return res
                return None
            found = scan_list(progress)
        if found:
            for check in ('claimed', 'is_claimed', 'claimed_at', 'status', 'state'):
                val = found.get(check)
                if val is not None:
                    if isinstance(val, bool):
                        return bool(val)
                    if isinstance(val, str):
                        lower = val.lower()
                        if 'claim' in lower or 'done' in lower or 'true' in lower:
                            return True
                        if 'un' in lower or 'false' in lower:
                            return False
                    if isinstance(val, (int, float)):
                        return bool(val)
            if 'user' in found or 'owner' in found:
                return True
            return None
        return None
    except Exception:
        return None

def claim_drop_reward(reward_id, campaign_id, cookies, max_attempts=3):
    print("[Stuxan] DEBUG cookies:", cookies)
    session_token = None
    if "session_token" in cookies:
        session_token = cookies.get("session_token")
    else:
        for k in cookies:
            if "session" in k:
                session_token = cookies[k]
                print("[Stuxan] session_token FOUND USING SCAN:", session_token)
                break
    print(f"[Stuxan] session_token value: {session_token}")
    if not session_token or len(str(session_token)) < 40:
        print("[Stuxan] ERROR: session_token missing or invalid, CLAIM ABORTED")
        return {'error': 'session_token missing or invalid'}
    if claim_manager.is_processed(reward_key):
        return None
    remote_status = _is_reward_claimed_remote(cookies, reward_key, campaign_id)
    if remote_status is True:
        claim_manager.mark_claimed(reward_key, str(campaign_id))
        return None
    reserved = claim_manager.reserve(reward_key, str(campaign_id))
    if not reserved:
        return None
    try:
        payload = {
            "reward_id": reward_id,
            "campaign_id": campaign_id
        }
        base_wait = 1.5
        session = None
        for attempt in range(max_attempts):
            proxy = get_proxy_or_none()
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
                response = s.post('https://web.kick.com/api/v1/drops/claim', json=payload, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('message') == 'Success' or result.get('data'):
                        claim_manager.mark_claimed(reward_key, str(campaign_id))
                        return result
                    msg = str(result.get('message') or result)
                    if 'already' in msg.lower() or 'claimed' in msg.lower():
                        claim_manager.mark_claimed(reward_key, str(campaign_id))
                        return result
                else:
                    text_preview = response.text[:400]
                    if response.status_code in (403, 410, 409):
                        if 'already' in text_preview.lower() or 'claimed' in text_preview.lower():
                            claim_manager.mark_claimed(reward_key, str(campaign_id))
                            return response.json() if response.text else None
            except Exception:
                pass
            finally:
                try:
                    if session:
                        session.close()
                except Exception:
                    pass
            if attempt < max_attempts - 1:
                wait = base_wait * (2 ** attempt) + random.random()
                time.sleep(min(wait, 15))
        claim_manager.release_reservation(reward_key)
        return None
    except Exception:
        claim_manager.release_reservation(reward_key)
        return None

def get_drops_progress(cookies, max_attempts=3):
    session_token = cookies.get('session_token')
    if not session_token:
        return None
    for attempt in range(max_attempts):
        proxy = get_proxy_or_none()
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
        except Exception:
            pass
        finally:
            s.close()
    return None

def get_random_stream_from_category(category_id, limit=10):
    headers = DEFAULT_HEADERS
    url = f'https://web.kick.com/api/v1/livestreams?limit={limit}&sort=viewer_count_desc&category_id={category_id}'
    proxy = get_proxy_or_none()
    response = requests.get(url, headers=headers, impersonate="chrome120", proxies=proxy)
    data = response.json()
    result = {'username': None, 'channel_id': None}
    if data and 'data' in data:
        livestreams = data['data'].get('livestreams', [])
        if livestreams:
            max_index = min(4, len(livestreams) - 1)
            random_index = random.randint(1, max_index) if max_index >= 1 else 0
            random_stream = livestreams[random_index]
            channel = random_stream.get('channel', {})
            result['username'] = channel.get('username')
            result['channel_id'] = channel.get('id')
    return result

async def get_stream_info(username):
    headers = DEFAULT_HEADERS
    url = f'https://kick.com/api/v2/channels/{username}/videos'
    result = {'is_live': False, 'game_id': None, 'game_name': None, 'live_stream_id': None}
    proxy = get_proxy_or_none()
    async with AsyncSession(impersonate="chrome120", proxies=proxy) as session:
        try:
            response = await session.get(url, headers=headers)
            data = response.json()
            if data and len(data) > 0:
                first_stream = data[0]
                result['is_live'] = first_stream.get('is_live', False)
                result['live_stream_id'] = first_stream.get('id')
                categories = first_stream.get('categories', [])
                if categories:
                    result['game_id'] = categories[0].get('id')
                    result['game_name'] = categories[0].get('name')
        except Exception:
            pass
    return result

def get_channel_id(channel_name, cookies=None):
    max_attempts = 3
    for attempt in range(max_attempts):
        proxy = get_proxy_or_none()
        s = requests.Session(impersonate="chrome120", proxies=proxy)
        if cookies:
            s.cookies.update(cookies)
        try:
            s.headers.update(DEFAULT_HEADERS)
            r = s.get(f"https://kick.com/api/v2/channels/{channel_name}", timeout=10)
            if r.status_code == 200:
                channel_id = r.json().get("id")
                return channel_id
        except Exception:
            pass
        time.sleep(2)
    return None

def get_token_with_cookies(cookies):
    max_attempts = 5
    session_token = cookies.get('session_token')
    if not session_token:
        return None
    for attempt in range(max_attempts):
        proxy = get_proxy_or_none()
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
            r = s.get('https://websockets.kick.com/viewer/v1/token', timeout=10)
            if r.status_code == 200:
                data = r.json()
                token = data.get("data", {}).get("token")
                if token:
                    return token
        except Exception:
            pass
        time.sleep(3 + attempt)
    return None

async def connection_channel(channel_id, username, category, token):
    max_retries = 10
    retry_count = 0
    current_info = await get_stream_info(username)
    watch_start_time = time.time()
    last_report_time = watch_start_time
    while retry_count < max_retries:
        try:
            if not current_info['is_live']:
                break
            proxy = get_proxy_or_none()
            async with AsyncSession(proxies=proxy, impersonate="chrome120", verify=False) as session:
                headers = DEFAULT_HEADERS
                ws = await session.ws_connect(f"wss://websockets.kick.com/viewer/v1/connect?token={token}", headers=headers)
                retry_count = 0
                counter = 0
                category_changed = False
                while True:
                    counter += 1
                    try:
                        if counter % 2 == 0:
                            await ws.send_json({"type": "ping"})
                        else:
                            await ws.send_json({"type": "channel_handshake", "data": {"message": {"channelId": channel_id}}})
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        except asyncio.TimeoutError:
                            pass
                        delay = 11 + random.randint(2, 7)
                        rndgamecheck = random.randint(1, 3)
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
                            current_info = await get_stream_info(username)
                            if current_info['game_id'] is not None and category != current_info['game_id']:
                                category_changed = True
                                break
                            if not current_info['is_live']:
                                category_changed = True
                                break
                        await asyncio.sleep(delay)
                    except Exception:
                        break
                if category_changed:
                    return category_changed
        except Exception:
            retry_count += 1
            if retry_count < max_retries:
                wait = random.randint(5, 10)
                await asyncio.sleep(wait)
            else:
                break