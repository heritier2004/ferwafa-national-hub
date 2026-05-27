"""
AI Pitch Machine — Main Entry Point
Starts a local FastAPI server on port 7777 serving:
- Control Panel UI (browser-based)
- /status, /logs, /config REST endpoints
- /control/start, /pause, /resume, /stop
"""
import asyncio
import sys
import os
import uvicorn
import subprocess
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from ai_machine.config import Config
from ai_machine.connection import AIConnection
from ai_machine.processor import AIVideoProcessingEngine

# ── App State ──────────────────────────────────────────────────────
config = Config()
connection: AIConnection = None
processor: AIVideoProcessingEngine = None
test_mode = False
test_frames = 0
test_events = 0
authenticated = False

app = FastAPI(title="AI Pitch Machine Control Panel", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UI_DIR = Path(__file__).parent / "ui"


# ── Serve UI Routes ────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if not authenticated:
        return HTMLResponse((UI_DIR / "login.html").read_text(encoding="utf-8"))
    
    html_path = UI_DIR / "index.html"
    if html_path.exists():
        response = HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        return response
    return HTMLResponse("<h1>Index not found</h1>", status_code=404)


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    if not authenticated:
        return HTMLResponse((UI_DIR / "login.html").read_text(encoding="utf-8"))
        
    html_path = UI_DIR / "control_panel.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Control Panel not found</h1>", status_code=404)


# ── Auth Endpoints ────────────────────────────────────────────────
@app.post("/auth/login")
async def login(data: dict):
    global authenticated
    u = data.get("username")
    p = data.get("password")
    
    # Secure Authority Credentials
    if u == "admin" and p == "ferwafa2024":
        authenticated = True
        return {"success": True}
    return JSONResponse({"success": False}, status_code=401)


@app.get("/auth/logout")
async def logout():
    global authenticated
    authenticated = False
    return {"success": True}


# ── Status Endpoint ────────────────────────────────────────────────
@app.get("/status")
async def get_status():
    global test_frames, test_events
    
    # Model Availability
    from ai_machine.processor import YOLO_AVAILABLE, OCR_AVAILABLE
    
    if test_mode:
        test_frames += 24
        if test_frames % 100 == 0: test_events += 1
        return {
            "configured": True,
            "connected": True,
            "processing": True,
            "paused": False,
            "frames_processed": test_frames,
            "events_sent": test_events,
            "match_minute": 45,
            "video_source": "MOCK_TEST_FEED",
            "api_key": "TEST_KEY_ACTIVE",
            "match_token": "TEST_TOKEN_ACTIVE",
            "server_url": "ws://mock.ferwafa.rw",
            "kit_home": "#FF0000",
            "kit_away": "#0000FF",
            "yolo_active": True,
            "tracker_active": True,
            "ocr_active": True,
            "device": "MOCK_GPU"
        }

    return {
        "configured": config.is_configured(),
        "connected": connection.is_connected if connection else False,
        "processing": processor.is_running if processor else False,
        "paused": processor.is_paused if processor else False,
        "frames_processed": processor.frames_processed if processor else 0,
        "events_sent": connection.events_sent if connection else 0,
        "match_minute": processor.match_minute() if processor else 0,
        "video_source": config.video_source_raw,
        "api_key": config.api_key,
        "match_token": config.match_token[:8] + "..." if config.match_token else "",
        "server_url": config.server_url,
        "kit_home": config.kit_home,
        "kit_away": config.kit_away,
        "yolo_active": YOLO_AVAILABLE and processor and processor.model is not None,
        "tracker_active": YOLO_AVAILABLE and processor and processor.is_running,
        "ocr_active": OCR_AVAILABLE and processor and processor.reader is not None,
        "device": config.device
    }


# ── Logs Endpoint ──────────────────────────────────────────────────
@app.get("/logs")
async def get_logs():
    logs = processor.get_logs(100) if processor else []
    return {"logs": logs}


# ── Detected Players Endpoint ──────────────────────────────────────
@app.get("/detected_players")
async def get_detected_players():
    if not processor:
        return {"players": []}
    
    # Return a list of players currently mapped in identity_map
    players = []
    for track_id, data in processor.identity_map.items():
        players.append({
            "track_id": track_id,
            "player_id": data.get("player_id"),
            "name": data.get("name"),
            "jersey": data.get("jersey"),
            "confidence": data.get("confidence")
        })
    return {"players": players}


# ── Config GET/POST ────────────────────────────────────────────────
@app.get("/config")
async def get_config():
    return config.to_dict()


@app.post("/config")
async def save_config(data: dict):
    config.update(data)
    config.save()
    return {"success": True, "message": "Configuration updated"}


# ── Control Endpoints ──────────────────────────────────────────────
@app.post("/control/start")
async def start_analysis():
    global connection, processor

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "Not configured — run setup wizard first"}, status_code=400)

    if processor and processor.is_running:
        return {"success": False, "error": "Already running"}

    # 1. Secure AI Handshake (signed)
    import urllib.request
    import json
    import hmac, hashlib
    
    url = f"{config.http_url}/api/ai/handshake"
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": "initialize_session"
    }
    msg_string = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        config.api_key.encode(),
        msg_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    packet = json.dumps({
        "payload": payload,
        "signature": signature,
        "match_token": config.match_token,
        "api_key": config.api_key
    }).encode('utf-8')

    squad_list = []
    venue_metadata = {}
    server_time_iso = None
    try:
        req = urllib.request.Request(url, data=packet, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("valid"):
                squad_list = data.get("squad", [])
                venue_metadata = {
                    "location_id": data.get("location_id"),
                    "region": data.get("region"),
                    "district": data.get("district"),
                    "venue_quality": data.get("venue_quality"),
                    "pitch_type": data.get("pitch_type"),
                    "has_floodlights": data.get("has_floodlights")
                }
                config.update({
                    "kit_home": data.get("kit_home", "#FF0000"),
                    "kit_home_socks": data.get("kit_home_socks", "#FFFFFF"),
                    "kit_away": data.get("kit_away", "#0000FF"),
                    "kit_away_socks": data.get("kit_away_socks", "#FFFFFF")
                })
                config.save()
                server_time_iso = data.get("server_time_iso")
            else:
                return JSONResponse({"success": False, "error": data.get("detail", "Handshake failed")}, status_code=401)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Secure Handshake failed: {e}"}, status_code=401)

    # 2. Start Managed Connection
    connection = AIConnection(config)
    if server_time_iso:
        connection.sync_time(server_time_iso)
    await connection.start()

    # 3. Start processing with full squad and location awareness
    processor = AIVideoProcessingEngine(config, connection, squad_list, venue_metadata, loop=asyncio.get_running_loop())
    processor.start() # Start the background OS thread
    return {"success": True, "message": "Analysis started with automated database sync in background"}


@app.post("/control/pause")
async def pause_analysis():
    if processor and processor.is_running:
        if processor.is_paused:
            processor.is_paused = False
            return {"success": True, "message": "Resumed"}
        else:
            processor.is_paused = True
            return {"success": True, "message": "Paused"}
    return {"success": False, "error": "Not running"}


@app.post("/control/stop")
async def stop_analysis():
    global test_mode, test_frames, test_events
    test_mode = False
    test_frames = 0
    test_events = 0
    if processor:
        processor.is_running = False
    if connection:
        if hasattr(connection, 'stop'):
            await connection.stop()
        elif hasattr(connection, 'disconnect'):
            await connection.disconnect()
    return {"success": True, "message": "Analysis stopped"}


@app.post("/control/connect-phone")
async def connect_phone_usb():
    try:
        # Run adb forward command to pull video from phone IP Webcam server via USB
        result = subprocess.run(
            ["adb", "forward", "tcp:8080", "tcp:8080"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return {"success": True, "message": "Phone USB Bridge Established. Source set to IP Webcam."}
        else:
            return {"success": False, "error": f"ADB failed: {result.stderr.strip()}. Ensure USB Debugging is on."}
    except FileNotFoundError:
         return {"success": False, "error": "ADB is not installed or not in PATH. Please install Android Platform Tools."}
    except Exception as e:
         return {"success": False, "error": str(e)}


@app.post("/control/test")
async def toggle_test_mode():
    global test_mode
    test_mode = not test_mode
    return {"success": True, "test_mode": test_mode}


# ── Entrypoint ─────────────────────────────────────────────────────
def start_server():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7777, log_level="error")

def main():
    print("\n" + "="*55)
    print("  ⚡  AI PITCH MACHINE  —  CONTROL DESKTOP APP")
    print("="*55)

    if not config.is_configured():
        print("\n  ⚠️  Not configured. Please configure in the Desktop App.\n")

    if config.autostart:
        print("  Auto-start enabled — beginning analysis...\n")
        import threading
        def auto():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_analysis())
        threading.Thread(target=auto, daemon=True).start()

    # Start FastAPI Web Server in Background
    import threading
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Start Native Window GUI in Foreground
    try:
        import webview
        import time
        time.sleep(1)  # small buffer to ensure uvicorn is listening before browser paints
        print("  🖥️  Opening National Hub Interface...")
        webview.create_window("National Football Intelligence System", "http://127.0.0.1:7777", width=1280, height=850, background_color="#020509")
        webview.start()
    except Exception as e:
        print(f"\n  ⚠️  Native GUI unavailable: {e}")
        print("  🚀 Server is still running. Access manually at: http://127.0.0.1:7777")
        # Keep the main thread alive since uvicorn is in a daemon thread
        while True:
            import time
            time.sleep(10)


if __name__ == "__main__":
    main()
