import time

class EventExtractor:
    def __init__(self):
        self.last_positions = {} # track_id -> (x, y, time)

    def process_frame(self, frame_data, match_id):
        events = []
        for obj in frame_data:
            track_id = obj["track_id"]
            pos = obj["position"]
            current_time = time.time()

            # Calculate speed/displacement
            if track_id in self.last_positions:
                prev_x, prev_y, prev_time = self.last_positions[track_id]
                dist = ((pos["x"] - prev_x)**2 + (pos["y"] - prev_y)**2)**0.5
                dt = current_time - prev_time
                if dt > 0:
                    speed = dist / dt
                    # If high speed, maybe a sprint
                    if speed > 700: # Threshold in pixel/sec
                        events.append({
                            "match_id": match_id,
                            "player_id": track_id, # Simplified mapping
                            "event_type": "sprint",
                            "value": speed
                        })
            
            self.last_positions[track_id] = (pos["x"], pos["y"], current_time)

        return events
