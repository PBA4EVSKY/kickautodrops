import json
import os
import configparser
import shutil
import sys

def ensure_config():
    if not os.path.exists("config.ini"):
        if os.path.exists("example_config.ini"):
            shutil.copy("example_config.ini", "config.ini")
            print("[INFO] config.ini created from example_config.ini.")
        else:
            print("[ERROR] example_config.ini not found. Please create it manually.")
            sys.exit(1)

def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini", encoding="utf-8")

    if "general" not in config or "language" not in config["general"]:
        print("[WARN] 'language' not found in config.ini. Defaulting to 'en'.")
        return "en"

    return config["general"]["language"]

def load_translation(lang_code: str):
    path = os.path.join("locales", f"{lang_code}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[WARN] Translation file {lang_code}.json not found, using English.")
        with open(os.path.join("locales", "en.json"), "r", encoding="utf-8") as f:
            return json.load(f)

ensure_config()
current_lang = load_config()
c = load_translation(current_lang)
