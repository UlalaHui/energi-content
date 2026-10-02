"""Tiny Telegram Bot API sender used by the daily run (no Hermes needed).
Reads TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from energi-content/.env, falling back to Hermes' .env."""
import os
import pathlib

import requests

from common import ROOT


def _read_env(path):
    out = {}
    p = pathlib.Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def creds():
    proj = _read_env(ROOT / ".env")
    herm = _read_env(pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / ".env")
    token = proj.get("TELEGRAM_BOT_TOKEN") or herm.get("TELEGRAM_BOT_TOKEN")
    chat = (proj.get("TELEGRAM_CHAT_ID") or herm.get("TELEGRAM_HOME_CHANNEL")
            or (herm.get("TELEGRAM_ALLOWED_USERS", "").split(",")[0].strip()))
    if not token or not chat:
        raise SystemExit("Telegram token/chat id not found. Add TELEGRAM_CHAT_ID (and TELEGRAM_BOT_TOKEN) to energi-content/.env")
    return token, chat


def _call(method, data=None, files=None):
    token, chat = creds()
    data = dict(data or {}, chat_id=chat)
    for i in range(3):
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=data, files=files, timeout=300)
            if r.ok:
                return r.json()
            print(f"telegram {method} HTTP {r.status_code}: {r.text[:200]}")
        except requests.RequestException as e:
            print(f"telegram {method} error: {e}")
    return None


def send(text):
    for i in range(0, len(text), 3900):          # Telegram limit 4096 chars
        _call("sendMessage", {"text": text[i:i + 3900], "disable_web_page_preview": "true"})


def photo(path, caption=""):
    with open(path, "rb") as f:
        _call("sendPhoto", {"caption": caption[:1000]}, {"photo": f})


def video(path, caption=""):
    with open(path, "rb") as f:
        _call("sendVideo", {"caption": caption[:1000], "supports_streaming": "true"}, {"video": f})
