"""
Event Extractor
Derives discrete match events (goals, shots, fouls, passes)
from consecutive frame tracking data.
All logic runs ONLY on the AI Pitch Machine.
"""
import math
from collections import defaultdict, deque
from datetime import datetime


class EventExtractor:
    """
    Stateful event detector — maintains history across frames
    to detect patterns that indicate football events.
    """

    def __init__(self, fps: float = 25.0):
        self.fps = fps
        self.frame_count = 0
        self.match_minute = 0

        # Tracking history: track_id -> deque of positions [(x,y)]
        self._positions: dict = defaultdict(lambda: deque(maxlen=60))
        # Ball position history
        self._ball_history: deque = deque(maxlen=120)
        # Last known ball position
        self._last_ball = None
        # Detected events buffer (emitted once, then cleared)
        self._event_buffer: list = []
        # Goal zones (normalized 0-100 coordinates)
        self._goal_left  = (2, 40, 60)   # x_max, y_min, y_max
        self._goal_right = (98, 40, 60)  # x_min, y_min, y_max
        # Anti-spam: last event type -> frame it was fired
        self._last_event_frame: dict = {}
        self._COOLDOWN_FRAMES = 75  # ~3 seconds at 25fps

        # Possession tracking
        self._possession_frames = {'home': 0, 'away': 0}
        self.stats = {
            'possession_home': 50.0,
            'total_distance': 0.0,
            'avg_speed': 0.0,
            'shots': 0,
            'fouls': 0
        }

    def _cooldown_ok(self, event_type: str) -> bool:
        last = self._last_event_frame.get(event_type, -9999)
        return (self.frame_count - last) > self._COOLDOWN_FRAMES

    def _fire_event(self, event_type: str, team: str = 'home',
                    player_id=None, confidence: float = 1.0, 
                    ocr_conf: float = 0, det_conf: float = 0, track_conf: float = 0,
                    extra: dict = None) -> dict:
        self._last_event_frame[event_type] = self.frame_count
        evt = {
            "type": "match_event",
            "event_type": event_type,
            "team": team,
            "player_id": player_id,
            "ai_confidence": round(confidence, 2),
            "ocr_conf": round(ocr_conf, 2),
            "det_conf": round(det_conf, 2),
            "track_conf": round(track_conf, 2),
            "minute": self.match_minute,
            "source": "ai_machine"
        }
        if extra:
            evt.update(extra)
        return evt

    def _distance(self, p1, p2) -> float:
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def _in_goal_zone(self, x: float, y: float) -> str | None:
        """Returns 'left' or 'right' if ball is in goal zone, else None."""
        x_l, y_min, y_max = self._goal_left
        if x <= x_l and y_min <= y <= y_max:
            return 'left'
        x_r, _, _ = self._goal_right
        if x >= x_r and y_min <= y <= y_max:
            return 'right'
        return None

    def process_frame(self, frame_data: dict, match_minute: int = 0) -> list:
        """
        Process one frame of tracking data and return any new events.
        """
        self.frame_count += 1
        self.match_minute = match_minute
        events = []

        players = frame_data.get('players', [])
        ball    = frame_data.get('ball')

        # Update player position histories
        for p in players:
            tid = p.get('track_id')
            if tid is not None:
                self._positions[tid].append((p['x'], p['y']))

        # Ball history
        if ball:
            self._ball_history.append((ball['x'], ball['y']))
            self._last_ball = ball

        # ── Possession estimation ─────────────────────────────────────
        if ball and players:
            nearest_p = self._nearest_player_to_ball(ball, players)
            if nearest_p:
                team = nearest_p.get('team')
                if team in ('home', 'away'):
                    self._possession_frames[team] += 1

        total_pos = sum(self._possession_frames.values()) or 1
        self.stats['possession_home'] = (self._possession_frames['home'] / total_pos) * 100

        # ── Goal detection ────────────────────────────────────────────
        if ball and self._cooldown_ok('goal'):
            zone = self._in_goal_zone(ball['x'], ball['y'])
            if zone:
                team_scoring = 'home' if zone == 'right' else 'away'
                # Find nearest player to ball at time of goal for credit
                n_p = self._nearest_player_to_ball(ball, players)
                events.append(self._fire_event(
                    'goal', 
                    team=team_scoring, 
                    player_id=n_p.get('player_id') if n_p else None,
                    confidence=n_p.get('confidence', 0.5) if n_p else 0.4,
                    ocr_conf=n_p.get('ocr_conf', 0) if n_p else 0,
                    det_conf=n_p.get('det_conf', 0) if n_p else 0,
                    track_conf=n_p.get('track_conf', 0) if n_p else 0,
                    extra={'detected': True}
                ))

        # ── Shot detection (fast ball movement toward goal) ──────────
        if len(self._ball_history) >= 10 and self._cooldown_ok('shot'):
            prev = self._ball_history[-10]
            curr = (ball['x'], ball['y']) if ball else (prev[0], prev[1])
            speed = self._distance(prev, curr)
            if speed > 15:
                n_p = self._nearest_player_to_ball(ball, players)
                events.append(self._fire_event(
                    'shot', 
                    player_id=n_p.get('player_id') if n_p else None,
                    confidence=n_p.get('confidence', 0.5) if n_p else 0.4,
                    ocr_conf=n_p.get('ocr_conf', 0) if n_p else 0,
                    det_conf=n_p.get('det_conf', 0) if n_p else 0,
                    track_conf=n_p.get('track_conf', 0) if n_p else 0,
                    extra={'ball_speed': round(speed, 1)}
                ))
                self.stats['shots'] += 1

        # ── Speed / distance stats (every 25 frames) ─────────────────
        if self.frame_count % 25 == 0 and players:
            speeds = []
            for p in players:
                tid = p.get('track_id')
                hist = self._positions.get(tid)
                if hist and len(hist) >= 5:
                    dist = self._distance(hist[-5], hist[-1])
                    speed_kmh = dist * self.fps / 5 * 0.036
                    speeds.append(speed_kmh)
            if speeds:
                self.stats['avg_speed'] = round(sum(speeds)/len(speeds), 2)
                self.stats['total_distance'] = round(
                    self.stats.get('total_distance', 0) + (sum(speeds) * 25 / self.fps / 1000), 3
                )

        return events

    def _nearest_player_to_ball(self, ball: dict, players: list) -> dict | None:
        min_d = float('inf')
        nearest = None
        for p in players:
            d = self._distance((ball['x'], ball['y']), (p['x'], p['y']))
            if d < min_d:
                min_d = d
                nearest = p
        return nearest

    def get_stats(self) -> dict:
        return dict(self.stats)
inf')
        team = None
        for p in players:
            d = self._distance((ball['x'], ball['y']), (p['x'], p['y']))
            if d < min_d:
                min_d = d
                team = p.get('team')
        return team

    def get_stats(self) -> dict:
        return dict(self.stats)
