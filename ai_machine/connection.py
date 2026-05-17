import asyncio
import json
import websockets
import uuid
import time
from datetime import datetime
import sqlite3
import os


class AIConnection:
    def __init__(self, config):
        self.config = config
        self.ws = None
        self.is_connected = False
        self.events_sent = 0
        self._log_cb = None
        self.time_offset = 0 # seconds
        
        # Resilience: SQLite Offline Buffer
        self.db_path = "offline_buffer.db"
        self._init_db()
        self._stop_event = asyncio.Event()
        self._worker_task = None
        self._heartbeat_task = None

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS pending_events
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()

    def set_log_callback(self, cb):
        self._log_cb = cb

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        if self._log_cb: self._log_cb(line)

    def sync_time(self, server_time_iso: str):
        """Calculates clock drift between local machine and authoritative server."""
        try:
            from dateutil.parser import parse
            server_dt = parse(server_time_iso)
            local_dt = datetime.utcnow()
            self.time_offset = (server_dt - local_dt).total_seconds()
            self.log(f"⏰ Server Time Synced (Offset: {self.time_offset:+.3f}s)")
        except Exception as e:
            self.log(f"⚠️ Time sync failed: {e}")

    async def start(self):
        """Starts the connection worker and heartbeat task."""
        self._worker_task = asyncio.create_task(self._buffer_worker())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.log("🚀 Connection manager started")

    async def stop(self):
        self._stop_event.set()
        if self._worker_task: self._worker_task.cancel()
        if self._heartbeat_task: self._heartbeat_task.cancel()
        if self.ws: await self.ws.close()
        self.is_connected = False
        self.log("🔌 Connection manager stopped")

    async def _heartbeat_loop(self):
        """Sends a heartbeat to the server every 5 seconds to monitor connection status."""
        while not self._stop_event.is_set():
            if self.is_connected:
                await self.send_event({"type": "heartbeat", "time": time.time()})
            await asyncio.sleep(5)

    async def _buffer_worker(self):
        """Background worker that manages the connection and flushes the event buffer."""
        import hmac
        import hashlib
        
        while not self._stop_event.is_set():
            if not self.is_connected:
                await self._attempt_connection()
                if not self.is_connected:
                    await asyncio.sleep(5) # Throttle retries
                    continue

            # Flush the buffer from SQLite
            try:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("SELECT id, payload FROM pending_events ORDER BY id ASC LIMIT 1")
                row = c.fetchone()
                
                if not row:
                    conn.close()
                    await asyncio.sleep(0.5)
                    continue
                    
                event_id, payload_str = row
                payload = json.loads(payload_str)
                
                # Sign the payload (Immutable Ledger Security)
                msgString = json.dumps(payload, sort_keys=True)
                signature = hmac.new(
                    self.config.api_key.encode(),
                    msgString.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                packet = {
                    "payload": payload,
                    "signature": signature
                }
                
                await self.ws.send(json.dumps(packet))
                self.events_sent += 1
                
                # Mark as synced (delete from buffer)
                c.execute("DELETE FROM pending_events WHERE id = ?", (event_id,))
                conn.commit()
                conn.close()
            except websockets.exceptions.ConnectionClosed:
                self.is_connected = False
                self.log("⚠️ Connection lost — buffering events...")
            except Exception as e:
                self.log(f"⚠️ Worker error: {e}")
                self.is_connected = False

    async def _attempt_connection(self):
        url = (
            f"{self.config.server_url}/ws/ai-ingest"
            f"?token={self.config.match_token}&key={self.config.api_key}"
        )
        try:
            self.ws = await websockets.connect(url, ping_interval=20, ping_timeout=10)
            self.is_connected = True
            self.log("✅ Server Connection Restored — Flushing Buffer")
        except Exception:
            self.is_connected = False

    async def send_event(self, event: dict):
        """Queues an event for delivery. Adds unique ID and timestamp."""
        # Add metadata for server-side validation and duplicate prevention
        if "source_event_id" not in event:
            event["source_event_id"] = str(uuid.uuid4())
        # Authoritative Timestamping (normalized to server time)
        if "timestamp" not in event:
            from datetime import timedelta
            norm_dt = datetime.utcnow() + timedelta(seconds=self.time_offset)
            event["timestamp"] = norm_dt.isoformat()
            
        # Write to persistent offline buffer
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Enforce max size ~10000 events to prevent massive disk bloat
            c.execute("SELECT COUNT(*) FROM pending_events")
            if c.fetchone()[0] > 10000:
                c.execute("DELETE FROM pending_events WHERE id = (SELECT MIN(id) FROM pending_events)")
            c.execute("INSERT INTO pending_events (payload) VALUES (?)", (json.dumps(event),))
            conn.commit()
            conn.close()
        except Exception as e:
            self.log(f"⚠️ Buffer write failed: {e}")

    async def send_tracking_update(self, players: list, ball: dict, stats: dict):
        """Send a full frame tracking snapshot."""
        # Low priority: only queue if not too backed up to prioritize match events
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM pending_events")
            count = c.fetchone()[0]
            conn.close()
            if count > 100:
                return
        except Exception:
            pass
            
        await self.send_event({
            "type": "player_position_update",
            "players": players
        })
        if ball:
            await self.send_event({
                "type": "ball_tracking_update",
                "ball": ball
            })
        if stats:
            await self.send_event({
                "type": "match_stats_update",
                **stats
            })

    async def send_match_event(self, event_type: str, player_id=None, minute: int = 0,
                                team: str = "home", extra: dict = None, confidence: float = 1.0):
        """Send a discrete match event (goal, foul, card, etc.)."""
        # Map simple types to requested event types
        type_map = {
            "goal": "goal_event",
            "foul": "foul_event",
            "yellow_card": "card_event",
            "red_card": "card_event",
            "substitution": "substitution_event"
        }
        
        payload = {
            "type": type_map.get(event_type, "match_event"),
            "event_type": event_type,
            "player_id": player_id,
            "minute": minute,
            "team": team,
            "ai_confidence": confidence
        }
        if extra:
            payload.update(extra)
        await self.send_event(payload)
        self.log(f"📤 Event queued: {event_type} @ {minute}' (Conf: {confidence:.2f})")
