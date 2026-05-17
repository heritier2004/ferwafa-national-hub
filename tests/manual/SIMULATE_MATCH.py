import asyncio
import websockets
import json
import hmac
import hashlib
import time

# --- CONFIG ---
TOKEN = "MATCH-2026-DEMO"
API_KEY = "FWFA-APR-2026-893A"
BACKEND_WS = f"ws://localhost:8001/ws/ai-ingest?token={TOKEN}&key={API_KEY}"

def create_payload(data):
    msg_string = json.dumps(data, sort_keys=True)
    signature = hmac.new(
        API_KEY.encode(),
        msg_string.encode(),
        hashlib.sha256
    ).hexdigest()
    return {
        "signature": signature,
        "payload": data
    }

async def run_simulation():
    print(f"Connecting to {BACKEND_WS}...")
    try:
        async with websockets.connect(BACKEND_WS) as ws:
            print("CONNECTION ESTABLISHED")
            
            # 1. Send Heatbeat
            await ws.send(json.dumps(create_payload({"type": "heartbeat"})))
            
            # 2. Simulate 90 seconds of play
            for i in range(90):
                # Mock Stats Update
                stats = {
                    "type": "stats_update",
                    "possession_home": 52 + (i % 3),
                    "avg_speed": 22.5 + (i * 0.1),
                    "total_distance": 2.4 + (i * 0.05)
                }
                await ws.send(json.dumps(create_payload(stats)))
                
                # Mock Tracking Update
                tracking = {
                    "type": "tracking_update",
                    "players": [
                        {"x": 45 + (i*0.2), "y": 30, "team": "home", "player_id": 1},
                        {"x": 55 - (i*0.2), "y": 60, "team": "away", "player_id": 12}
                    ],
                    "ball": {"x": 50 + (i*0.1), "y": 45}
                }
                await ws.send(json.dumps(create_payload(tracking)))
                
                if i == 5:
                    print("SIMULATING GOAL...")
                    goal = {
                        "type": "match_event",
                        "event_type": "goal",
                        "team": "home",
                        "player_id": 1,
                        "minute": 12,
                        "ai_confidence": 0.95,
                        "x": 99.5, "y": 50,
                        "source_event_id": f"evt_{int(time.time())}"
                    }
                    await ws.send(json.dumps(create_payload(goal)))

                print(f"[{i}] Sent frame update...")
                await asyncio.sleep(1)
            
            print("Simulation Complete.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_simulation())
