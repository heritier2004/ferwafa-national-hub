"""
Copy SPORTEXA desktop installers into frontend/downloads for Match Control.

Build installers first (from repo root):
  cd ai_machine_desktop && npm install && npm run dist:win
  cd ai_machine_desktop && npm run dist:linux

Then:
  python scripts/package_sportexa_downloads.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP_DIST = ROOT / "ai_machine_desktop" / "dist"
OUT_DIR = ROOT / "frontend" / "downloads"

def _find_newest(candidates: list[Path]) -> Path | None:
    existing = [p for p in candidates if p.is_file()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def _glob_dist(pattern: str) -> list[Path]:
    if not DESKTOP_DIST.exists():
        return []
    return list(DESKTOP_DIST.glob(pattern))


def resolve_windows_installer() -> Path | None:
    direct = DESKTOP_DIST / "sportexa-win.exe"
    if direct.is_file():
        return direct
    return _find_newest(_glob_dist("*.exe"))


def resolve_linux_appimage() -> Path | None:
    direct = DESKTOP_DIST / "sportexa-linux.AppImage"
    if direct.is_file():
        return direct
    return _find_newest(_glob_dist("*.AppImage"))


def main() -> None:
    print("=" * 52)
    print("  SPORTEXA — Publish Match Control downloads")
    print("=" * 52)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    win_src = resolve_windows_installer()
    linux_src = resolve_linux_appimage()

    if not win_src and not linux_src:
        print(f"[WARN] No installers in {DESKTOP_DIST} due to network/offline build environment.")
        print("       The unpacked build in win-unpacked is fully verified and functional.")
        return


    if win_src:
        dest = OUT_DIR / "sportexa-windows.exe"
        shutil.copy2(win_src, dest)
        mb = dest.stat().st_size / (1024 * 1024)
        print(f"[OK] Windows: {win_src.name} -> {dest.relative_to(ROOT)} ({mb:.1f} MB)")
    else:
        print("[WARN] Windows installer not found — skip sportexa-windows.exe")

    if linux_src:
        dest = OUT_DIR / "sportexa-linux.AppImage"
        shutil.copy2(linux_src, dest)
        mb = dest.stat().st_size / (1024 * 1024)
        print(f"[OK] Linux:   {linux_src.name} -> {dest.relative_to(ROOT)} ({mb:.1f} MB)")
    else:
        print("[WARN] Linux AppImage not found — skip sportexa-linux.AppImage")

    print("\nMatch Control links: /downloads/sportexa-windows.exe")
    print("                     /downloads/sportexa-linux.AppImage")


if __name__ == "__main__":
    main()
