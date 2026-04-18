import json

class OutputFormatter:
    @staticmethod
    def format_tracking_data(frame_data):
        """
        Formats raw tracking data for the frontend tactical pitch.
        """
        payload = []
        for obj in frame_data:
            payload.append({
                "id": obj["track_id"],
                "x": obj["position"]["x"],
                "y": obj["position"]["y"],
                "type": obj["class"],
                "team": "home" # Logic for team identification would go here
            })
        return {
            "type": "tracking",
            "payload": payload
        }

    @staticmethod
    def format_event_data(event):
        """
        Formats an event for the frontend event log.
        """
        return {
            "type": "event",
            "payload": {
                "time": "15", # Mock minute
                "type": event["event_type"],
                "player": f"ID {event['player_id']}",
                "team": "home"
            }
        }
