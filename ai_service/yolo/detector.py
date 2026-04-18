from ultralytics import YOLO
import cv2
import json

class FootballDetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.model = YOLO(model_path)
        
    def detect_and_track(self, frame_source):
        # Using ByteTrack via ultralytics
        results = self.model.track(
            source=frame_source, 
            persist=True, 
            tracker="bytetrack.yaml",
            classes=[0, 32] # 0: person (player), 32: sports ball
        )
        return results

    def extract_frame_data(self, results):
        frame_data = []
        if results and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            cls = results[0].boxes.cls.int().cpu().tolist()
            
            for box, track_id, cl in zip(boxes, track_ids, cls):
                x1, y1, x2, y2 = box
                frame_data.append({
                    "track_id": track_id,
                    "class": "player" if cl == 0 else "ball",
                    "position": {"x": (x1 + x2) / 2, "y": (y1 + y2) / 2},
                    "bbox": [float(x1), float(y1), float(x2), float(y2)]
                })
        return frame_data
