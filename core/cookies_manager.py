import traceback
import os
from core import tl
from http.cookiejar import MozillaCookieJar

def _msg(key: str, **kwargs) -> str:
    fallback_templates = {
        "file_empty": "Cookie file {file_path} is empty",
        "cookies_loaded": "Cookies loaded from {file_path}",
        "cookies_file_notfound": "Cookie file {file_path} not found",
        "cookies_error_load": "Error loading cookies: {e}"
    }
    try:
        template = None
        if isinstance(getattr(tl, "c", None), dict):
            template = tl.c.get(key)
        if not template:
            template = fallback_templates.get(key, "")
        return template.format(**kwargs)
    except Exception:
        if "e" in kwargs:
            return f"Error loading cookies: {kwargs['e']}"
        return "Message formatting error"

def load_cookies(file_path="cookies.txt", silent=False):
    cookies_dict = {}
    try:
        cookie_jar = MozillaCookieJar(file_path)
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        for cookie in cookie_jar:
            cookies_dict[cookie.name] = cookie.value.strip()
        if not cookies_dict:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 7:
                            cname = parts[5]
                            cvalue = parts[6].strip()
                            cookies_dict[cname] = cvalue
        if not cookies_dict:
            if not silent:
                print(_msg("file_empty", file_path=file_path))
            return None
        session_token = cookies_dict.get('session_token')
        if not session_token or len(session_token) < 40:
            if not silent:
                print(f"[Stuxan] Warning: session_token not found or too short in {file_path}")
        if not silent:
            print(_msg("cookies_loaded", file_path=file_path))
        return cookies_dict
    except FileNotFoundError:
        if not silent:
            print(_msg("cookies_file_notfound", file_path=file_path))
        return None
    except Exception as e:
        if not silent:
            try:
                print(_msg("cookies_error_load", e=e))
            except Exception:
                print("Error loading cookies:", e)
            traceback.print_exc()
        return None