import threading
import subprocess
import time
import sys
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from core import kick;
from core import tl;

app = Flask(__name__)
app.secret_key = os.environ.get("STUXAN_WEBUI_KEY", "kicksecretkey")  # change on production!

LOG_LINES = 300
farmer_process = None
farmer_logs = []
farmer_lock = threading.Lock()

selected_game_id = None
selected_drop_type = "streamers"
LOGIN_PASSWORD = os.environ.get("KICK_WEBUI_PASS", "kickminer")  # change on production!

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_games():
    sys.path.insert(0, get_project_root())
    campaigns_resp = kick.get_all_campaigns()
    seen = set()
    games = []
    for camp in campaigns_resp.get("data", []):
        cat = camp.get("category", {})
        cat_id = str(cat.get("id"))
        if not cat_id or cat_id in seen:
            continue
        image = cat.get("icon") or "/static/default_game.png"
        games.append({"id": cat_id, "name": cat.get("name", "Unknown"), "image": image})
        seen.add(cat_id)
    return games

def get_drop_status(game_id, drop_type):
    sys.path.insert(0, get_project_root())

    cookies = {}
    cookies_path = os.path.join(get_project_root(), "cookies.txt")
    if os.path.exists(cookies_path):
        with open(cookies_path, "r", encoding="utf-8") as f:
            for line in f:
                if len(line.split("\t")) >= 7:
                    cookies[line.split("\t")[5]] = line.split("\t")[6]

    campaigns_resp = kick.get_all_campaigns()
    progress_data = kick.get_drops_progress(cookies)

    game_camps = []
    for camp in campaigns_resp.get("data", []):
        if str(camp.get("category", {}).get("id")) == str(game_id):
            item = camp.copy()
            item["progress"] = {}
            item["rewards"] = camp.get("rewards", [])
            if progress_data and "data" in progress_data:
                for p_camp in progress_data["data"]:
                    if str(p_camp.get("id")) == str(camp.get("id")):
                        for rw in item["rewards"]:
                            stat = next((r for r in p_camp.get("rewards", []) if str(r['id']) == str(rw['id'])), None)
                            if stat:
                                rw["claimed"] = stat.get("claimed", False)
                                rw["progress"] = stat.get("progress", 0)
            game_camps.append(item)
    return game_camps

def start_farmer(game_id, drop_type):
    global farmer_process, farmer_logs
    with farmer_lock:
        if farmer_process and farmer_process.poll() is None:
            farmer_process.terminate()
            time.sleep(1)
        farmer_logs.clear()
        project_root = get_project_root()
        cmd = [
            sys.executable,
            "index.py",
            "--category", str(game_id),
            "--mode", drop_type
        ]
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        farmer_process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            env=env
        )
        def log_reader():
            for line in iter(farmer_process.stdout.readline, ''):
                farmer_logs.append(line.rstrip())
                if len(farmer_logs) > LOG_LINES:
                    del farmer_logs[0]
            farmer_process.stdout.close()
        threading.Thread(target=log_reader, daemon=True).start()

@app.route("/login", methods=["GET", "POST"])
def login():
    err = None
    if request.method == "POST":
        password = request.form.get("password")
        if password == LOGIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("main_page"))
        else:
            err = "Wrong password!"
    return render_template("login.html", error=err)

@app.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET"])
@login_required
def main_page():
    global selected_game_id, selected_drop_type
    games = get_games()
    drop_types = [
        ("streamers", "Streamers Drops"),
        ("general", "General Drops")
    ]
    if not games:
        return render_template("error.html", msg="No available campaigns/categories detected.")
    if not selected_game_id:
        selected_game_id = games[0]["id"]
    drop_status = get_drop_status(selected_game_id, selected_drop_type)
    start_farmer(selected_game_id, selected_drop_type)
    return render_template("index.html",
        games=games,
        drop_types=drop_types,
        current_game_id=selected_game_id,
        current_drop_type=selected_drop_type,
        drop_status=drop_status,
        farmer_status="RUNNING" if farmer_process and farmer_process.poll() is None else "STOPPED"
    )

@app.route("/api/select", methods=["POST"])
@login_required
def select():
    global selected_game_id, selected_drop_type
    data = request.get_json(force=True)
    game_id = data.get("game_id")
    drop_type = data.get("drop_type")
    if game_id:
        selected_game_id = game_id
    if drop_type:
        selected_drop_type = drop_type
    start_farmer(selected_game_id, selected_drop_type)
    drop_status = get_drop_status(selected_game_id, selected_drop_type)
    return jsonify({"ok": True, "drop_status": drop_status})

@app.route("/api/logs")
@login_required
def get_logs():
    global farmer_process
    status = "RUNNING" if farmer_process and farmer_process.poll() is None else "STOPPED"
    return jsonify({"logs": farmer_logs[-LOG_LINES:], "status": status})

@app.route("/api/drop_status")
@login_required
def drop_status_api():
    global selected_game_id, selected_drop_type
    drop_status = get_drop_status(selected_game_id, selected_drop_type)
    return jsonify({"drop_status": drop_status})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
