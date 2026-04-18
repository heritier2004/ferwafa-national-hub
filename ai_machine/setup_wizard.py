"""
AI Pitch Machine — First-Time Setup Wizard (CLI)
Guides the operator through entering API Key, Match Token,
selecting the video source, and saving the configuration.
"""
import sys
import os
import asyncio
import aiohttp
from ai_machine.config import Config


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def header():
    print("\033[92m" + "=" * 60 + "\033[0m")
    print("\033[92m   ⚡  AI PITCH MACHINE  —  SETUP WIZARD  \033[0m")
    print("\033[92m" + "=" * 60 + "\033[0m\n")


def section(title: str):
    print(f"\n\033[94m── {title} ──\033[0m")


def success(msg: str):
    print(f"\033[92m✅  {msg}\033[0m")


def error(msg: str):
    print(f"\033[91m❌  {msg}\033[0m")


def warn(msg: str):
    print(f"\033[93m⚠️   {msg}\033[0m")


async def test_connection(config: Config) -> bool:
    """Validate the API Key and Match Token against the server."""
    url = f"{config.http_url}/api/match/token/{config.match_token}/validate?key={config.api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("valid", False), data
                else:
                    return False, {}
    except Exception as e:
        return False, {"error": str(e)}


def run_wizard():
    clear()
    header()
    config = Config()

    print("  This wizard will configure your AI Pitch Machine.")
    print("  You need the API Key and Match Token from the Match Control page.\n")

    # ── Step 1: Server URL ──────────────────────────────────────────────
    section("STEP 1 — Server URL")
    print(f"  Current: {config._data['server_url']}")
    url_in = input("  Enter Server URL (press ENTER to keep current): ").strip()
    if url_in:
        config.update({
            "server_url": url_in.replace("http://", "ws://").replace("https://", "wss://"),
            "http_url": url_in if url_in.startswith("http") else "http://" + url_in.split("//")[-1]
        })

    # ── Step 2: API Key ─────────────────────────────────────────────────
    section("STEP 2 — API Key")
    print("  Found on the Match Control page (Setup tab).")
    print("  Format: FWFA-CLUBCODE-2026-XXXX\n")
    while True:
        key = input("  Paste API Key: ").strip()
        if key:
            config.update({"api_key": key})
            break
        warn("API Key cannot be empty.")

    # ── Step 3: Match Token ─────────────────────────────────────────────
    section("STEP 3 — Match Token")
    print("  Found on the Match Control page (Setup tab).\n")
    while True:
        token = input("  Paste Match Token (UUID): ").strip()
        if token:
            config.update({"match_token": token})
            break
        warn("Match Token cannot be empty.")

    # ── Step 4: Test connection ─────────────────────────────────────────
    section("STEP 4 — Validate Credentials")
    print("  Testing connection to server...")
    valid, data = asyncio.run(test_connection(config))
    if valid:
        success(f"Credentials VALID! Match: {data.get('home_team','?')} vs {data.get('opponent','?')}")
        config.update({"kit_home": data.get("kit_home", "#FF0000"), "kit_away": data.get("kit_away", "#0000FF")})
    else:
        error_msg = data.get("error") or data.get("detail") or "Unknown"
        error(f"Validation failed: {error_msg}")
        warn("Saving anyway — check credentials manually before starting analysis.")

    # ── Step 5: Video Source ──────────────────────────────────────────────
    section("STEP 5 — Video Input Source")
    print("  Select your camera / video input:\n")
    print("  [1] USB Camera (index 0 — default)")
    print("  [2] USB Camera (index 1 — secondary)")
    print("  [3] RTSP Stream (IP camera)")
    print("  [4] HDMI Capture Device (index 2)")
    print("  [5] YouTube / Live Stream URL (yt-dlp required)")
    print("  [6] Custom input")

    choice = input("\n  Enter choice [1-6]: ").strip()
    source_map = {"1": "0", "2": "1", "4": "2"}

    if choice in source_map:
        config.update({"video_source": source_map[choice], "video_source_type": "usb"})
        success(f"USB Camera index {source_map[choice]} selected")
    elif choice == "3":
        rtsp = input("  Enter RTSP URL (e.g. rtsp://192.168.1.100/stream): ").strip()
        config.update({"video_source": rtsp, "video_source_type": "rtsp"})
        success("RTSP stream configured")
    elif choice == "5":
        url = input("  Enter stream URL: ").strip()
        config.update({"video_source": url, "video_source_type": "url"})
        warn("Requires yt-dlp and ffmpeg to be installed on this system")
    elif choice == "6":
        custom = input("  Enter custom source: ").strip()
        config.update({"video_source": custom, "video_source_type": "custom"})
    else:
        config.update({"video_source": "0", "video_source_type": "usb"})
        warn("Default: USB Camera (index 0)")

    # ── Step 6: Auto-start ──────────────────────────────────────────────
    section("STEP 6 — Auto-Start")
    auto = input("  Start analysis automatically on machine boot? [y/N]: ").strip().lower()
    config.update({"autostart": auto == 'y'})

    # ── Save ──────────────────────────────────────────────────────────
    print()
    config.save()
    print()
    success("Configuration saved to ai_machine_config.json")
    print()
    print("  \033[94mNext steps:\033[0m")
    print("  1. Open your browser: \033[92mhttp://localhost:7777\033[0m")
    print("  2. Click  \033[92mSTART ANALYSIS\033[0m  to begin")
    print()

    return config


if __name__ == "__main__":
    run_wizard()
