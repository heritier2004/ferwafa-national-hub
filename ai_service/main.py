import asyncio
import cv2
from ai_service.yolo.detector import FootballDetector
from ai_service.pipeline.event_extractor import EventExtractor
import websockets
import json

class AIService:
    def __init__(self, video_source=0):
        self.detector = FootballDetector()
        self.extractor = EventExtractor()
        self.video_source = video_source
        self.match_id = 1 # Default for demo

    async def run(self):
        cap = cv2.VideoCapture(self.video_source)
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # AI Inference
            results = self.detector.detect_and_track(frame)
            frame_data = self.detector.extract_frame_data(results)
            
            # Event Extraction
            events = self.extractor.process_frame(frame_data, self.match_id)
            
            # Emit data (Simplified: directly to a mock WebSocket or logging)
            if events:
                print(f"Detected Events: {events}")
            
            # Yield control for async
            await asyncio.sleep(0.01)
            
        cap.release()

if __name__ == "__main__":
    service = AIService()
    asyncio.run(service.run())
