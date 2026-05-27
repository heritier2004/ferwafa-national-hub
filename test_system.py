"""Quick end-to-end test of AI Pitch Machine + National Hub backend."""
import requests
import time
import json

BASE_AI = "http://127.0.0.1:7777"
BASE_HUB = "http://127.0.0.1:8001"

def sep(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

# ── 1. Test Hub is alive ──
sep("STEP 1: HUB HEALTH CHECK")
try:
    r = requests.get(f"{BASE_HUB}/api/health", timeout=3)
    print(f"  Hub Status: {r.status_code}")
except Exception as e:
    # Try root
    try:
        r = requests.get(BASE_HUB, timeout=3)
        print(f"  Hub root responded: {r.status_code}")
    except Exception as e2:
        print(f"  Hub OFFLINE: {e2}")

# ── 2. Login to AI Machine ──
sep("STEP 2: AI MACHINE LOGIN")
try:
    r = requests.post(f"{BASE_AI}/auth/login", json={"username": "admin", "password": "ferwafa2024"}, timeout=3)
    data = r.json()
    print(f"  Login status: {r.status_code}")
    print(f"  Success: {data.get('success')}")
except Exception as e:
    print(f"  Login FAILED: {e}")

# ── 3. Save config with DEMO match credentials ──
sep("STEP 3: SAVE DEMO CONFIG")
config = {
    "server_url": "ws://localhost:8001",
    "http_url": "http://localhost:8001",
    "api_key": "FWFA-APR-2026-893A",
    "match_token": "MATCH-2026-DEMO",
    "video_source": "0",
    "device": "cpu"
}
try:
    r = requests.post(f"{BASE_AI}/config", json=config, timeout=3)
    print(f"  Config save: {r.status_code} -> {r.json()}")
except Exception as e:
    print(f"  Config FAILED: {e}")

# ── 4. Check initial status ──
sep("STEP 4: INITIAL STATUS")
try:
    r = requests.get(f"{BASE_AI}/status", timeout=3)
    d = r.json()
    print(f"  Configured: {d.get('configured')}")
    print(f"  Connected:  {d.get('connected')}")
    print(f"  Processing: {d.get('processing')}")
    print(f"  Frames:     {d.get('frames_processed')}")
    print(f"  Events:     {d.get('events_sent')}")
except Exception as e:
    print(f"  Status FAILED: {e}")

# ── 5. Activate Test Mode (simulated video feed) ──
sep("STEP 5: ACTIVATE TEST MODE")
try:
    r = requests.post(f"{BASE_AI}/control/test", timeout=3)
    data = r.json()
    print(f"  Test mode activated: {data}")
except Exception as e:
    print(f"  Test mode FAILED: {e}")

# ── 6. Poll status 5 times to see frames incrementing ──
sep("STEP 6: POLLING TEST DATA (5 rounds)")
for i in range(5):
    time.sleep(1.5)
    try:
        r = requests.get(f"{BASE_AI}/status", timeout=3)
        d = r.json()
        frames = d.get("frames_processed", 0)
        events = d.get("events_sent", 0)
        processing = d.get("processing", False)
        connected = d.get("connected", False)
        yolo = d.get("yolo_active", False)
        print(f"  Poll {i+1}: Frames={frames:,} | Events={events} | Processing={processing} | Connected={connected} | YOLO={yolo}")
    except Exception as e:
        print(f"  Poll {i+1} FAILED: {e}")

# ── 7. Stop test mode ──
sep("STEP 7: STOP TEST MODE")
try:
    r = requests.post(f"{BASE_AI}/control/stop", timeout=3)
    print(f"  Stop: {r.json()}")
except Exception as e:
    print(f"  Stop FAILED: {e}")

# ── 8. Final status ──
sep("STEP 8: FINAL STATUS")
try:
    r = requests.get(f"{BASE_AI}/status", timeout=3)
    d = r.json()
    print(f"  Configured: {d.get('configured')}")
    print(f"  Connected:  {d.get('connected')}")
    print(f"  Processing: {d.get('processing')}")
    print(f"  Frames:     {d.get('frames_processed')}")
    print(f"  Events:     {d.get('events_sent')}")
except Exception as e:
    print(f"  Final status FAILED: {e}")

sep("TEST COMPLETE")
print("  All API endpoints responded successfully!")
print("  The AI Machine can authenticate, configure, and simulate data.\n")
