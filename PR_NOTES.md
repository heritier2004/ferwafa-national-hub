# PR Notes for cleanup branches

These branches preserve all UI/UX files exactly as on `origin/main`.

## Branch `cleanup/relocate-yolo`
- Relocated YOLO model weights to `assets/models/yolov8n.pt`.
- Updated code paths and packaging references accordingly.
- Preserved all UI/UX files.
## Branch `cleanup/vulture-candidates`
- Applied safe static-analysis cleanup for high-confidence unused code.
- Restored all UI/UX files to `origin/main`.

# Smoke tests
Endpoints checked: backend `/` and ai_machine `/status`, plus ai login and `/config`.

# Notes
- UI/UX files were intentionally preserved and restored.
