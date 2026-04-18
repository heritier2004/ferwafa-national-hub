import asyncio
import json
import uuid
import time
import websockets
from datetime import datetime

class MatchSimulator:
    def __init__(self, match_id, match_token, api_key, base_url="ws://localhost:8000"):
        self.match_id = match_id
        self.match_token = match_token
        self.api_key = api_key
        self.ws_url = f"{base_url}/ws/ai_machine/{match_token}?key={api_key}"
        self.buffer = []

    async def run_scenario_network_drop(self):
        """Test: Network failure simulations (offloading buffer)."""
        print(f"\n[SCENARIO] Testing Network Drop & Buffer Recovery...")
        
        try:
            async with websockets.connect(self.ws_url) as ws:
                # 1. Send normal events
                evt1 = self._create_event("goal", 0.95)
                await ws.send(json.dumps(evt1))
                print("✅ Sent initial event (confirmed)")
                
                # 2. Simulate Drop (Close connection)
                print("⚠️ Simulating Network DROP for 5 seconds...")
                # We close manually to simulate connection lost
                await ws.close()
                
            # 3. Buffer events while offline
            buffered_evt = self._create_event("goal", 0.85)
            self.buffer.append(buffered_evt)
            print(f"📦 Local buffer active: {len(self.buffer)} events stored")
            await asyncio.sleep(2)
            
            # 4. Reconnect and Flush
            print("🔄 Reconnecting and FLUSHING buffer...")
            async with websockets.connect(self.ws_url) as ws:
                for e in self.buffer:
                    await ws.send(json.dumps(e))
                self.buffer = []
                print("✅ Buffer flushed successfully")
        except Exception as e:
            print(f"❌ Error during network drop test: {e}")

    async def run_scenario_idempotency(self):
        """Test: Duplicate event testing (UUID check)."""
        print(f"\n[SCENARIO] Testing UUID Idempotency (Duplicate Prevention)...")
        evt = self._create_event("foul", 0.9)
        
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Send same event twice
                await ws.send(json.dumps(evt))
                print("✅ Sent event first time")
                await asyncio.sleep(1)
                await ws.send(json.dumps(evt))
                print("✅ Sent duplicate event (Same Event ID)")
                print("💡 Server should reject the second one in the DB.")
        except Exception as e:
            print(f"❌ Error during idempotency test: {e}")

    async def run_scenario_ocr_failure(self):
        """Test: OCR Failure/Noise (Low Confidence) tiered workflow."""
        print(f"\n[SCENARIO] Testing OCR Low Confidence (Unconfirmed workflow)...")
        
        # Scenario: High tracking trust but muddy jersey (Low OCR)
        evt = self._create_event("yellow_card", 0.65, ocr_c=0.4, track_c=0.9)
        
        try:
            async with websockets.connect(self.ws_url) as ws:
                await ws.send(json.dumps(evt))
                print(f"✅ Sent event with 65% confidence (OCR: 40%)")
                print("💡 Should appear as UNCONFIRMED on dashboard.")
        except Exception as e:
            print(f"❌ Error during OCR failure test: {e}")

    def _create_event(self, etype, conf, ocr_c=0.9, track_c=0.9):
        return {
            "type": "match_event",
            "event_type": etype,
            "source_event_id": str(uuid.uuid4()),
            "ai_confidence": conf,
            "ocr_conf": ocr_c,
            "track_conf": track_c,
            "det_conf": 0.95,
            "minute": 15,
            "team": "home",
            "x": 50, "y": 30
        }

async def main():
    print("🚀 Starting AI Pitch Machine Simulation Suite")
    print("---------------------------------------------")
    
    # Placeholder credentials - in real test these must match a created session
    sim = MatchSimulator(
        match_id=1, 
        match_token="REPLACE_WITH_VALID_TOKEN", 
        api_key="REPLACE_WITH_VALID_KEY"
    )
    
    await sim.run_scenario_network_drop()
    await sim.run_scenario_idempotency()
    await sim.run_scenario_ocr_failure()

if __name__ == "__main__":
    asyncio.run(main())
