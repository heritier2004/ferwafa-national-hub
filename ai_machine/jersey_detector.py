"""
Jersey Color Detector
Uses HSV color histogram comparison to classify players as home or away team.
This runs ONLY on the AI Pitch Machine — never on the Match Page.
"""
import numpy as np
import cv2


def hex_to_bgr(hex_color: str) -> tuple:
    """Convert hex color string (#RRGGBB) to BGR tuple for OpenCV."""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (b, g, r)


def hex_to_hsv(hex_color: str) -> np.ndarray:
    """Convert hex to HSV numpy array (1x1 pixel) for comparison."""
    bgr = np.uint8([[list(hex_to_bgr(hex_color))]])
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]


def color_distance_hsv(hsv1: np.ndarray, hsv2: np.ndarray) -> float:
    """
    Compute weighted Euclidean distance in HSV space.
    Hue is circular (0-179 in OpenCV), so we handle wrap-around.
    """
    h1, s1, v1 = float(hsv1[0]), float(hsv1[1]), float(hsv1[2])
    h2, s2, v2 = float(hsv2[0]), float(hsv2[1]), float(hsv2[2])

    # Hue distance (circular, 0-180)
    dh = min(abs(h1 - h2), 180 - abs(h1 - h2))
    ds = abs(s1 - s2)
    dv = abs(v1 - v2)

    # Weight: hue matters most for jersey distinction
    return (dh * 2.0) ** 2 + (ds * 0.5) ** 2 + (dv * 0.3) ** 2


class JerseyDetector:
    """
    Classifies a player bounding box as 'home', 'away', or 'referee'.
    Uses dominant color extraction from the torso region and lower legs region.
    """

    def __init__(self, kit_home: str = "#FF0000", kit_away: str = "#0000FF", kit_home_socks: str = "#FFFFFF", kit_away_socks: str = "#FFFFFF"):
        self.update_kits(kit_home, kit_away, kit_home_socks, kit_away_socks)
        # Referee typically wears black or bright yellow — approximate
        self._referee_hsv = hex_to_hsv("#000000")

    def update_kits(self, kit_home: str, kit_away: str, kit_home_socks: str = "#FFFFFF", kit_away_socks: str = "#FFFFFF"):
        self.kit_home_hex = kit_home
        self.kit_away_hex = kit_away
        self.kit_home_socks_hex = kit_home_socks
        self.kit_away_socks_hex = kit_away_socks
        
        self.kit_home_hsv = hex_to_hsv(kit_home)
        self.kit_away_hsv = hex_to_hsv(kit_away)
        self.kit_home_socks_hsv = hex_to_hsv(kit_home_socks)
        self.kit_away_socks_hsv = hex_to_hsv(kit_away_socks)

    def _extract_torso(self, frame: np.ndarray, bbox) -> np.ndarray:
        """Crop the torso region (middle third of bounding box height)."""
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        h = y2 - y1
        # Torso = middle third
        t_y1 = y1 + h // 3
        t_y2 = y1 + (h * 2) // 3
        t_x1 = x1 + (x2 - x1) // 4
        t_x2 = x2 - (x2 - x1) // 4
        # Bounds check
        t_y1, t_y2 = max(0, t_y1), min(frame.shape[0], t_y2)
        t_x1, t_x2 = max(0, t_x1), min(frame.shape[1], t_x2)
        if t_y2 <= t_y1 or t_x2 <= t_x1:
            return None
        return frame[t_y1:t_y2, t_x1:t_x2]

    def _extract_legs(self, frame: np.ndarray, bbox) -> np.ndarray:
        """Crop the legs/socks region (bottom third of bounding box height)."""
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        h = y2 - y1
        # Legs = bottom third
        t_y1 = y1 + (h * 2) // 3
        t_y2 = y2
        t_x1 = x1 + (x2 - x1) // 4
        t_x2 = x2 - (x2 - x1) // 4
        # Bounds check
        t_y1, t_y2 = max(0, t_y1), min(frame.shape[0], t_y2)
        t_x1, t_x2 = max(0, t_x1), min(frame.shape[1], t_x2)
        if t_y2 <= t_y1 or t_x2 <= t_x1:
            return None
        return frame[t_y1:t_y2, t_x1:t_x2]

    def _dominant_hsv(self, region: np.ndarray) -> np.ndarray:
        """Return the median HSV value from the region (robust to noise)."""
        if region is None or region.size == 0:
            return np.array([0, 0, 128])
        hsv_region = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        # Flatten and compute median across all pixels
        pixels = hsv_region.reshape(-1, 3)
        return np.median(pixels, axis=0).astype(np.uint8)

    def classify(self, frame: np.ndarray, bbox) -> str:
        """
        Returns: 'home', 'away', or 'unknown'
        """
        torso = self._extract_torso(frame, bbox)
        legs = self._extract_legs(frame, bbox)
        
        if torso is None or legs is None:
            return 'unknown'

        dom_torso = self._dominant_hsv(torso)
        dom_legs = self._dominant_hsv(legs)
        
        # Calculate distances combining torso (shirt) and legs (socks)
        dist_home_torso = color_distance_hsv(dom_torso, self.kit_home_hsv)
        dist_home_legs = color_distance_hsv(dom_legs, self.kit_home_socks_hsv)
        dist_home = dist_home_torso + (dist_home_legs * 0.5)  # give slightly less weight to socks
        
        dist_away_torso = color_distance_hsv(dom_torso, self.kit_away_hsv)
        dist_away_legs = color_distance_hsv(dom_legs, self.kit_away_socks_hsv)
        dist_away = dist_away_torso + (dist_away_legs * 0.5)

        # If too similar to either, return unknown
        # Since we added leg distances, the threshold should be considered carefully. 
        # (8000 threshold from before applied to one color. For two colors, maybe 12000)
        if min(dist_home, dist_away) > 12000:
            return 'unknown'

        return 'home' if dist_home < dist_away else 'away'

    def classify_batch(self, frame: np.ndarray, bboxes: list) -> list:
        """Classify a list of bounding boxes. Returns list of team strings."""
        return [self.classify(frame, bbox) for bbox in bboxes]
