import traceback
from core import tl
from core import events
from http.cookiejar import MozillaCookieJar

def load_cookies(file_path="cookies.txt"):
    try:
        cookie_jar = MozillaCookieJar(file_path)
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        
        cookies_dict = {}
        for cookie in cookie_jar:
            cookies_dict[cookie.name] = cookie.value
        
        if not cookies_dict:
            events.emit(events.EventType.ERROR, tl.c["file_empty"].format(file_path=file_path))
            return None

        events.emit(events.EventType.SUCCESS, tl.c["cookies_loaded"].format(file_path=file_path))
        return cookies_dict
        
    except FileNotFoundError:
        events.emit(events.EventType.ERROR, tl.c["cookies_file_notfound"].format(file_path=file_path))
        return None
    except Exception as e:
        events.emit(events.EventType.ERROR, tl.c["cookies_error_load"].format(e=e))
        events.emit(events.EventType.ERROR, traceback.format_exc())
        return None