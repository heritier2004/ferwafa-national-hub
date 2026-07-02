# file: c:/Users/User/Documents/NEW_VERSION/ai_machine/create_desktop_icon.py
import os
import sys
import subprocess
import platform
from pathlib import Path

def _ensure_winshell():
    """Ensure winshell and pywin32 are available.
    If missing, install them into the current virtual environment.
    """
    try:
        import winshell  # noqa: F401
        from win32com.client import Dispatch  # noqa: F401
    except Exception:
        print("[*] Installing missing Windows shortcut libraries …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "winshell", "pywin32"])
        # Reload modules to confirm success
        import importlib
        importlib.import_module("winshell")
        importlib.import_module("win32com.client")

def _venv_python_path(app_dir: Path) -> Path:
    """Return absolute path to the venv's python.exe."""
    return app_dir / ".venv" / "Scripts" / "python.exe"

def _create_shortcut(target_py: Path, python_exe: Path, icon_path: Path, shortcut_path: Path):
    """Create a .lnk file that runs the AI machine.
    Args:
        target_py: Path to main.py
        python_exe: Path to the venv python executable
        icon_path: Path to an .ico file (optional)
        shortcut_path: Destination .lnk file on the desktop
    """
    from win32com.client import Dispatch
    import winshell

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(python_exe)
    # Quote the script path – essential if directories contain spaces.
    shortcut.Arguments = f'"{target_py}"'
    shortcut.WorkingDirectory = str(target_py.parent)
    shortcut.IconLocation = str(icon_path) if icon_path.exists() else str(python_exe)
    shortcut.Description = "FERWAFA National Football Intelligence – AI Pitch Machine"
    shortcut.save()
    print(f"[+] Shortcut created at: {shortcut_path}")

def create_shortcut():
    # ---- 1️⃣ Detect OS -------------------------------------------------
    if platform.system() != "Windows":
        print("[!] This script is Windows‑only. Use the provided *.sh for macOS/Linux.")
        return

    # ---- 2️⃣ Ensure shortcut‑creation libs are present --------------------
    _ensure_winshell()
    import winshell

    # ---- 3️⃣ Resolve paths -------------------------------------------------
    app_dir = Path(__file__).resolve().parent
    python_exe = _venv_python_path(app_dir)
    main_py = app_dir / "main.py"
    ico_path = app_dir / "assets" / "icon.ico"
    shortcut_path = Path(winshell.desktop()) / "FERWAFA AI Pitch.lnk"

    # ---- 4️⃣ Ensure the virtual environment exists ----------------------
    if not python_exe.exists():
        print("[*] Virtual environment not found – creating now …")
        subprocess.check_call([sys.executable, "-m", "venv", str(app_dir / ".venv")])
        # Upgrade pip and install core requirements (mirrors install_and_launch.bat)
        subprocess.check_call([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([
            str(python_exe), "-m", "pip", "install",
            "torch", "torchvision", "torchaudio",
            "ultralytics", "opencv-python", "easyocr",
            "requests", "winshell", "pypiwin32",
            "fastapi", "uvicorn", "pywebview", "websockets",
            "aiohttp", "python-dotenv"
        ])

    # ---- 5️⃣ Create the .lnk ------------------------------------------------
    try:
        _create_shortcut(main_py, python_exe, ico_path, shortcut_path)
    except Exception as e:
        print(f"[!] Failed to create the shortcut: {e}")
        print("[*] As a fallback, run the following command manually:")
        print(f'    "{python_exe}" "{main_py}"')
        return

if __name__ == "__main__":
    create_shortcut()
