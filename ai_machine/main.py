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
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ai_machine.config import Config
from ai_machine.connection import AIConnection
from ai_machine.processor import VideoProcessor

# ── App State ──────────────────────────────────────────────────────
config = Config()
connection: AIConnection = None
processor: VideoProcessor = None
_processing_task = None

app = FastAPI(title="AI Pitch Machine Control Panel", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UI_DIR = Path(__file__).parent / "ui"


# ── Serve Control Panel UI ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_path = UI_DIR / "control_panel.html"
    if html_path.exists():
        response = HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return HTMLResponse("<h1>Control Panel not found</h1>", status_code=404)


# ── Status Endpoint ────────────────────────────────────────────────
@app.get("/status")
async def get_status():
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
        "kit_away": config.kit_away
    }


# ── Logs Endpoint ──────────────────────────────────────────────────
@app.get("/logs")
async def get_logs():
    logs = processor.get_logs(100) if processor else []
    return {"logs": logs}


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
    global connection, processor, _processing_task

    if not config.is_configured():
        return JSONResponse({"success": False, "error": "Not configured — run setup wizard first"}, status_code=400)

    if processor and processor.is_running:
        return {"success": False, "error": "Already running"}

    # 1. Fetch match context (kit colors, etc) via HTTP
    import urllib.request
    import json
    url = f"{config.http_url}/api/match/token/{config.match_token}/validate?key={config.api_key}"
    squad_list = []
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("valid"):
                squad_list = data.get("squad", [])
                config.update({
                    "kit_home": data.get("kit_home", "#FF0000"),
                    "kit_home_socks": data.get("kit_home_socks", "#FFFFFF"),
                    "kit_away": data.get("kit_away", "#0000FF"),
                    "kit_away_socks": data.get("kit_away_socks", "#FFFFFF")
                })
                config.save()
                server_time_iso = data.get("server_time_iso")
            else:
                return JSONResponse({"success": False, "error": data.get("detail", "Invalid API Key or Match Token")}, status_code=401)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Auth failed: {e}"}, status_code=401)

    # 2. Start Managed Connection
    connection = AIConnection(config)
    if server_time_iso:
        connection.sync_time(server_time_iso)
    await connection.start()

    # 3. Start processing with full squad awareness
    processor = VideoProcessor(config, connection, squad_list)
    _processing_task = asyncio.create_task(processor.run())
    return {"success": True, "message": "Analysis started with automated database sync"}


@app.post("/control/pause")
async def pause_analysis():
    if processor and processor.is_running:
        if processor.is_paused:
            processor.resume()
            return {"success": True, "message": "Resumed"}
        else:
            processor.pause()
            return {"success": True, "message": "Paused"}
    return {"success": False, "error": "Not running"}


@app.post("/control/stop")
async def stop_analysis():
    global _processing_task
    if processor:
        processor.stop()
    if connection:
        await connection.disconnect()
    if _processing_task and not _processing_task.done():
        _processing_task.cancel()
    return {"success": True, "message": "Analysis stopped"}


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
    import webview
    import time
    time.sleep(1)  # small buffer to ensure uvicorn is listening before browser paints
    webview.create_window("AI Pitch Machine", "http://127.0.0.1:7777", width=1200, height=800, background_color="#020509")
    webview.start()


if __name__ == "__main__":
    main()
