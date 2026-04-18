import cv2
import numpy as np

class VideoProcessor:
    def __init__(self, source):
        self.source = source
        self.cap = cv2.VideoCapture(source)

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def preprocess(self, frame, size=(640, 640)):
        """
        Resizes and normalizes frame for YOLO inference.
        """
        resized = cv2.resize(frame, size)
        # Add normalization or other transforms if needed
        return resized

    def release(self):
        self.cap.release()

    @staticmethod
    def draw_annotations(frame, frame_data):
        """
        Utility to draw bboxes on frames for debugging.
        """
        for obj in frame_data:
            bbox = obj["bbox"]
            label = f"{obj['track_id']} {obj['class']}"
            cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (0, 255, 0), 2)
            cv2.putText(frame, label, (int(bbox[0]), int(bbox[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame
