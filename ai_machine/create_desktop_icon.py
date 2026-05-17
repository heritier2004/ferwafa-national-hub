import os
import platform
import sys

def create_shortcut():
    current_os = platform.system()
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # We want to launch with the virtual environment's python
    if current_os == "Windows":
        python_exe = os.path.join(app_dir, ".venv", "Scripts", "python.exe")
        script_path = os.path.join(app_dir, "main.py")
        ico_path = os.path.join(app_dir, "assets", "icon.ico") # Placeholder for icon
        
        try:
            import winshell
            from win32com.client import Dispatch

            desktop = winshell.desktop()
            path = os.path.join(desktop, "FERWAFA AI Pitch.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = python_exe
            shortcut.Arguments = f'"{script_path}"'
            shortcut.WorkingDirectory = app_dir
            shortcut.IconLocation = ico_path if os.path.exists(ico_path) else python_exe
            shortcut.Description = "FERWAFA National Football Intelligence - AI Machine"
            shortcut.save()
            print(f"[+] Windows Shortcut created at: {path}")
        except Exception as e:
            print(f"[!] Could not create Windows shortcut: {e}")
            print("[*] Please manually create a link to start_windows.bat")

    elif current_os == "Darwin" or current_os == "Linux":
        # On Unix, we usually just ensure the starter script is executable
        # or create a .desktop file, but for now we'll rely on the .sh
        print(f"[*] On {current_os}, please use 'start_mac_linux.sh' as your primary launcher.")
        print("[*] You can pin it to your dock/panel manually.")

if __name__ == "__main__":
    create_shortcut()
