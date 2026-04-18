"""
AI Machine Configuration Manager
Reads and writes the local config file: ai_machine_config.json
"""
import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "ai_machine_config.json"

DEFAULTS = {
    "api_key": "",
    "match_token": "",
    "server_url": "ws://localhost:8001",
    "http_url": "http://localhost:8001",
    "video_source": "0",       # "0"=USB, "rtsp://...", "http://..."
    "video_source_type": "usb",  # usb | rtsp | url
    "autostart": False,
    "kit_home": "#FF0000",
    "kit_home_socks": "#FFFFFF",
    "kit_away": "#0000FF",
    "kit_away_socks": "#FFFFFF",
    "confidence_threshold": 0.45,
    "device": "cpu"            # "cpu" or "cuda"
}

class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except Exception as e:
                print(f"[Config] Warning: could not read config: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self._data, f, indent=2)
            print("[Config] Configuration saved.")
        except Exception as e:
            print(f"[Config] ERROR saving config: {e}")

    def update(self, data: dict):
        self._data.update(data)

    def is_configured(self) -> bool:
        return bool(self._data.get("api_key") and self._data.get("match_token"))

    # ── Property shortcuts ──────────────────────────────
    @property
    def api_key(self): return self._data.get("api_key", "")

    @property
    def match_token(self): return self._data.get("match_token", "")

    @property
    def server_url(self): return self._data.get("server_url", "ws://localhost:8001")

    @property
    def http_url(self): return self._data.get("http_url", "http://localhost:8001")

    @property
    def video_source(self):
        src = self._data.get("video_source", "0")
        return int(src) if src.isdigit() else src

    @property
    def video_source_raw(self): return self._data.get("video_source", "0")

    @property
    def device(self): return self._data.get("device", "cpu")

    @property
    def confidence_threshold(self): return float(self._data.get("confidence_threshold", 0.45))

    @property
    def kit_home(self): return self._data.get("kit_home", "#FF0000")

    @property
    def kit_home_socks(self): return self._data.get("kit_home_socks", "#FFFFFF")

    @property
    def kit_away(self): return self._data.get("kit_away", "#0000FF")

    @property
    def kit_away_socks(self): return self._data.get("kit_away_socks", "#FFFFFF")

    @property
    def autostart(self): return bool(self._data.get("autostart", False))

    def to_dict(self):
        return dict(self._data)
