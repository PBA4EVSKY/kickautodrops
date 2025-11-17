import json
import os
import configparser
import shutil
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) 

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.ini")

EXAMPLE_CONFIG_PATH = os.path.join(PROJECT_ROOT, "example_config.ini")

def ensure_config():
    if not os.path.exists(CONFIG_PATH):
        if not os.path.exists(EXAMPLE_CONFIG_PATH):
            raise FileNotFoundError("example_config.ini not found in project root: " + EXAMPLE_CONFIG_PATH)
        shutil.copy(EXAMPLE_CONFIG_PATH, CONFIG_PATH)

def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    if "general" not in config or "language" not in config["general"]:
        print("[WARN] 'language' not found in config.ini. Defaulting to 'en'.")
        return "en"

    return config["general"]["language"]

def load_translation(lang_code: str):
    path = os.path.join(PROJECT_ROOT, "locales", f"{lang_code}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[WARN] Translation file {lang_code}.json not found, using English.")
        with open(os.path.join("locales", "en.json"), "r", encoding="utf-8") as f:
            return json.load(f)
        
def get_proxy():
    config = configparser.ConfigParser()
    config.read("config.ini")
    proxy = config.get("network", "proxy", fallback=None)
    if proxy:
        return {"http": proxy, "https": proxy, "ws": proxy, "wss": proxy, "socks5": proxy}
    else:
        return None

config = configparser.ConfigParser()
ensure_config()
config.read(CONFIG_PATH)
current_lang = load_config()
c = load_translation(current_lang)
