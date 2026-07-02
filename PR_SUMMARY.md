Commit: b76ced523d4e1d856b953d2eed7cab160a700cfe
Title: Relocate YOLO weights to assets/models, add cleanup script, update .gitignore

Summary:
- Moved `yolov8n.pt` into `assets/models/yolov8n.pt` and updated code to prefer the new path.
- Added `scripts/cleanup.ps1` to remove regenerable artifacts.
- Updated `.gitignore` to exclude `assets/models/`, `node_modules/`, `dist_electron/`, and `ai_machine.zip`.
- Committed various frontend/backend UI updates surfaced during cleanup.

Changed files: see `git diff --name-only HEAD~1..HEAD` for full list.

Notes for reviewer:
- The `AI` service now prefers `assets/models/yolov8n.pt` but falls back to root `yolov8n.pt` if missing.
- `vulture` static scan was run; its report is in `vulture_report.txt` and candidates are in `vulture_candidates.md`.
- Tests (`test_system.py`) ran: hub and ai endpoints responded; test mode was exercised.

Suggested next steps:
- Review `vulture_candidates.md` before removing code.
- Push branch and open PR to remote; I can push if you provide the remote name.
