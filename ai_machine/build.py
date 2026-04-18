"""
AI Pitch Machine — Build Script
Packages the AI Machine as a standalone executable using PyInstaller.

Usage:
    python ai_machine/build.py [--platform windows|linux]

Output:
    dist/AIMatchMachine.exe  (Windows)
    dist/ai_match_machine    (Linux)
"""

import subprocess
import sys
import os
import shutil
import platform as pf

TARGET_PLATFORM = sys.argv[1] if len(sys.argv) > 1 else pf.system().lower()


def build_windows():
    print("🔨 Building for Windows (.exe)...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "AIMatchMachine",
        "--add-data", "ai_machine/ui;ui",
        "--add-data", "ai_machine/ai_machine_config.json;.",
        "--hidden-import", "ultralytics",
        "--hidden-import", "cv2",
        "--hidden-import", "websockets",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "webview",
        "--icon", "ai_machine/ui/icon.ico",
        "ai_machine/main.py"
    ]
    subprocess.run(cmd, check=True)
    print("✅ Windows build complete: dist/AIMatchMachine.exe")


def build_linux():
    print("🔨 Building for Linux (.sh installer)...")
    # PyInstaller binary
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "ai_match_machine",
        "--add-data", "ai_machine/ui:ui",
        "--hidden-import", "ultralytics",
        "--hidden-import", "cv2",
        "--hidden-import", "websockets",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "webview",
        "ai_machine/main.py"
    ]
    subprocess.run(cmd, check=True)

    # Create .sh installer wrapper
    installer = """#!/bin/bash
echo "Installing AI Pitch Machine..."
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"
cp ai_match_machine "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/ai_match_machine"
echo ""
echo "✅ Installed to $INSTALL_DIR/ai_match_machine"
echo "   Run: ai_match_machine"
"""
    with open("dist/install.sh", "w") as f:
        f.write(installer)
    os.chmod("dist/install.sh", 0o755)
    print("✅ Linux build complete: dist/ai_match_machine + dist/install.sh")


if __name__ == "__main__":
    print("=" * 55)
    print("  AI PITCH MACHINE — BUILD SYSTEM")
    print("=" * 55)

    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller not found. Install it:")
        print("   pip install pyinstaller")
        sys.exit(1)

    if "windows" in TARGET_PLATFORM:
        build_windows()
    elif "linux" in TARGET_PLATFORM:
        build_linux()
    else:
        print(f"⚠️  Unknown platform: {TARGET_PLATFORM}")
        print("   Use: python build.py windows  OR  python build.py linux")
        sys.exit(1)

    print("\n✅ Build complete. Check the dist/ directory.")
