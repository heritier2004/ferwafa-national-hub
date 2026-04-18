import asyncio
import cv2
import time
import queue
import threading
from datetime import datetime
from ai_machine.jersey_detector import JerseyDetector
from ai_machine.event_extractor import EventExtractor

# Try importing YOLO and EasyOCR
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class VideoProcessor:
    """
    Manages the full AI processing pipeline with automated database sync:
    YOLO (Boxes) → ByteTrack (IDs) → OCR (Identity Binding) → Database Mapping
    """

    def __init__(self, config, connection, squad_list=None):
        self.config = config
        self.connection = connection
        self.squad_list = squad_list or []

        self.is_running = False
        self.is_paused = False
        self.frames_processed = 0
        self.start_time = None
        self._logs = []
        self._log_cb = None

        # ── Identity Binding Logic ────────────────────────────────────
        # mapping: track_id -> { "player_id": id, "name": name, "confidence": float }
        self.identity_map = {}
        # queue for background OCR processing (prevents main loop lag)
        self.ocr_queue = queue.Queue(maxsize=10)
        self.ocr_results = {} # track_id -> jersey_number strings

        # Sub-systems
        self.jersey_detector = JerseyDetector(config.kit_home, config.kit_away, config.kit_home_socks, config.kit_away_socks)
        self.event_extractor = EventExtractor(fps=25.0)

        # YOLO model
        self.model = None
        if YOLO_AVAILABLE:
            try:
                self.log("Loading YOLOv8 model...")
                self.model = YOLO("yolov8n.pt")
                self.log("✅ YOLO model active")
            except Exception as e:
                self.log(f"⚠️ YOLO failed: {e}")

        # EasyOCR Reader
        self.reader = None
        if OCR_AVAILABLE:
            try:
                self.log("Initializing OCR Engine (Jersey Recognition)...")
                # Using English for simple digits
                self.reader = easyocr.Reader(['en'], gpu=config.device != "cpu")
            except Exception as e:
                self.log(f"⚠️ OCR Init failed: {e}")

    def set_log_callback(self, cb):
        self._log_cb = cb
        self.connection.set_log_callback(cb)

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        self._logs.append(line)
        if self._log_cb: self._log_cb(line)

    async def run(self):
        self.is_running = True
        self.start_time = time.time()
        
        # Start background OCR worker thread
        if self.reader:
            threading.Thread(target=self._ocr_worker, daemon=True).start()

        cap = cv2.VideoCapture(self.config.video_source)
        if not cap.isOpened():
            self.log(f"❌ Camera Source Failed: {self.config.video_source_raw}")
            await self._run_simulation()
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_delay = 1.0 / fps

        while self.is_running:
            if self.is_paused:
                await asyncio.sleep(0.1); continue

            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.5); continue

            # Core AI Pipeline
            frame_data = self._process_frame(frame)
            self.frames_processed += 1

            # Telemetry Refresh (Every 2 frames for higher speed data)
            if self.frames_processed % 2 == 0:
                await self.connection.send_tracking_update(
                    players=frame_data['players'],
                    ball=frame_data.get('ball'),
                    stats=self.event_extractor.get_stats()
                )

            # Event Extraction (with auto-sync identities)
            events = self.event_extractor.process_frame(frame_data, self.match_minute())
            for evt in events:
                # Add confidence score and db binding from the processor state
                await self.connection.send_event(evt)

            await asyncio.sleep(frame_delay * 0.7) # Dynamic speedup

        cap.release()

    def _process_frame(self, frame) -> dict:
        players = []
        ball = None
        h, w = frame.shape[:2]

        if not self.model: return {'players': [], 'ball': None}

        # Hardware Optimized Inference (imgsz=480 for speed)
        results = self.model.track(frame, persist=True, verbose=False, imgsz=480,
                                   conf=self.config.confidence_threshold,
                                   device=self.config.device)

        for r in results:
            if not r.boxes: continue
            for box in r.boxes:
                cls_id = int(box.cls[0]) if box.cls is not None else -1
                track_id = int(box.id[0]) if box.id is not None else None
                xyxy = box.xyxy[0].tolist()

                cx = ((xyxy[0] + xyxy[2]) / 2) / w * 100
                cy = ((xyxy[1] + xyxy[3]) / 2) / h * 100

                if cls_id == 0: # person
                    # 1. Detect Team
                    team = self.jersey_detector.classify(frame, xyxy)
                    
                    # 2. Bind Identity (Database Sync)
                    db_binding = self._resolve_identity(frame, track_id, team, xyxy)
                    
                    players.append({
                        'track_id': track_id,
                        'x': round(cx, 2),
                        'y': round(cy, 2),
                        'team': team,
                        'player_id': db_binding.get('player_id'),
                        'name': db_binding.get('name'),
                        'jersey': db_binding.get('jersey') or track_id,
                        'confidence': db_binding.get('confidence', 0.5),
                        'ocr_conf': db_binding.get('ocr_conf', 0),
                        'det_conf': 0.9, # YOLO Detection fixed trust
                        'track_conf': db_binding.get('track_conf', 0.5)
                    })
                elif cls_id == 32: # ball
                    ball = {'x': round(cx, 2), 'y': round(cy, 2)}

        return {'players': players, 'ball': ball}

    def _resolve_identity(self, frame, track_id, team, xyxy):
        """Maps an anonymous tracker to a Database Player ID via OCR or Fallback Context."""
        if track_id in self.identity_map:
            return self.identity_map[track_id]

        # 1. Check if we have an OCR result pending
        ocr_data = self.ocr_results.get(track_id) # now a dict: {num, conf}
        
        # 2. If no result, try to capture a crop
        if not ocr_data and track_id is not None and not self.ocr_queue.full():
            crop = self.jersey_detector._extract_torso(frame, xyxy)
            if crop is not None:
                self.ocr_queue.put((track_id, crop))

        # 3. If we found a number, match with the Database Squad List
        if ocr_data:
            detected_num = ocr_data.get('num')
            ocr_conf = ocr_data.get('conf', 0)
            for p in self.squad_list:
                if str(p.get('jersey')) == str(detected_num) and p.get('team') == team:
                    # Tiered Confidence Model Calculation
                    # Weighted blend: OCR (60%) + Tracking (40%)
                    track_trust = 0.95 # Assume tracking is high trust if we have a stable ID
                    total_conf = (ocr_conf * 0.6) + (track_trust * 0.4)
                    
                    self.identity_map[track_id] = {
                        "player_id": p.get('player_id'),
                        "name": p.get('name'),
                        "jersey": p.get('jersey'),
                        "confidence": total_conf,
                        "ocr_conf": ocr_conf,
                        "track_conf": track_trust
                    }
                    self.log(f"✅ Identity Bound: #{detected_num} -> {p.get('name')} (Conf: {total_conf:.2f})")
                    return self.identity_map[track_id]

        # 4. Fallback (tracking-only placeholder)
        return {"player_id": None, "name": f"P-{track_id}", "jersey": None, "confidence": 0.3, "ocr_conf": 0, "track_conf": 0.4}

    def _ocr_worker(self):
        """Background thread for jersey number recognition (tri-factor binding)."""
        while self.is_running:
            try:
                track_id, crop = self.ocr_queue.get(timeout=2)
                # OCR read
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                results = self.reader.readtext(gray, allowlist='0123456789')
                if results:
                    # Filter for confidence and digits
                    best = max(results, key=lambda x: x[2])
                    num_str = "".join(filter(str.isdigit, best[1]))
                    if num_str and best[2] > 0.4:
                        self.ocr_results[track_id] = num_str
                self.ocr_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[OCR_ERROR] {e}")

    async def _run_simulation(self):
        """Simulation mode (unchanged logic, for offline testing)."""
        self.log("🎮 Simulation active (no camera found)")
        while self.is_running:
            await asyncio.sleep(1) # placeholders
