# KickDropMiner — Web UI Edition

KickDropMiner automatically watches Kick livestreams and claims Drops. This fork(fully refactored) provides a single, local Web UI that lets you run, control, and monitor the farming process in the background.

## Features

- Web UI built with Flask: one dashboard to start/stop farming, view campaign progress, see logs, and claim rewards.
- All UI text is localization-ready (`locales/en.json` and multi-language support).
- Simple install: just Python, no external services required.

## Table of Contents

- [Requirements](#requirements)
- [Quick Setup](#quick-setup)
- [Running the Web UI](#running-the-web-ui)
- [Exporting Cookies](#exporting-cookies)
  - [Method A: cookies.txt extension](#method-a---cookiestxt-extension-recommended)
  - [Method B: browser export](#method-b---browser-extension--manual-export)
  - [Manual alternative: DevTools](#manual-alternative-devtools)
- [Configuration](#configuration)
- [Editing UI Text](#editing-ui-text)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Credits & License](#credits--license)

## Requirements

- Python 3.10 or newer (3.11+ recommended)
- Optional: Git
- A Kick account with an active session (`session_token`)
- (Recommended) Python virtual environment

## Quick Setup

1. **Clone or download the repository:**

   ```sh
   git clone https://github.com/Abolfazl74/kickdropminer.git
   cd kickdropminer
   ```

2. **Create & activate your virtual environment:**

   ```sh
   python -m venv .venv
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows PowerShell:
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

4. **Export and place your Kick cookies:**

   - Use one of the guides below to export cookies and save as `cookies.txt` in the project root (same folder as `index.py` and `app.py`).
   - The expected format is Netscape `cookies.txt` (see next section).

5. **Start the Web UI:**

   ```sh
   python webui/app.py
   # or
   python -m webui.app
   ```

   Open your browser at [http://localhost:8080](http://localhost:8080)

---

## Exporting Cookies

The farmer needs your `session_token` to authenticate to Kick's API. It's safest to export ALL cookies in Netscape format (`cookies.txt`).

### Method A — cookies.txt Extension (Recommended)

1. **Chrome (and Chromium-based browsers):**
   - Install the "cookies.txt" extension in the Chrome Web Store.
   - Log into Kick.com.
   - Click the extension icon and export cookies for the current site.
   - Save as `cookies.txt` and move to the repo root.

2. **Firefox:**
   - Install the "cookies.txt" extension from Firefox Add-ons.
   - Log into Kick.com, export cookies, save as `cookies.txt`, move it to the project root.

### Method B — Browser Extension + Manual Export

- Use a cookie manager browser extension to export cookies in plain text.
- Copy/export ALL cookies, save as `cookies.txt`.

### Manual Alternative — Using DevTools

If you only need the `session_token` cookie:

1. Open DevTools (F12), go to Application/Storage tab.
2. Find cookies for `https://kick.com` and locate the `session_token`.
3. Copy its value.
4. Create a `cookies.txt` file with the following (replace VALUE):

   ```
   kick.com	TRUE	/	FALSE	0	session_token	VALUE
   ```

_Note: The cookies.txt extension is safest—manual edits can break the format._

---

## Configuration

- Default Web UI port: **8080**
- Default password will be saved in `config.ini` file

- On first run, `config.ini` is created from `example_config.ini`. Edit it to change proxy settings or default language.

---

## Editing UI Text

- All UI strings are in `locales/en.json`.
- Change labels, messages, etc. by editing `locales/en.json` (keep key names).
- Templates use `tl.c[...]` or the `t` variable, so translations update automatically.

---

## Troubleshooting

- **No campaigns detected / missing progress:**
  - Ensure `cookies.txt` is present and correct.
  - Check logs (shown in Web UI).

- **Database locked / SQLite errors:**
  - This fork defaults to in-memory reservations. If using SQLite, shut down all processes before restarting.

- **Missing/thumbnails images:**
  - Kick's API may omit campaign images. Placeholder or best effort will be used.

---

## Security Notes

- Treat your `cookies.txt` like a password. Keep it private and secure!
- Do **not** expose the Web UI to the internet unless you add authentication and TLS.
- Change the default password for any non-localhost deployment.

---

## Development Notes

- The Web UI is in the `webui/` directory and manages background farmer processes (`index.py`) with live logs.
- All UI strings load from `locales/en.json`. For other locales, add files like `locales/es.json` and select language in `config.ini`.
- For advanced multi-worker setups, consider Redis or a coordination service.

---

## Credits & License

Made with ♥ by StuXan  