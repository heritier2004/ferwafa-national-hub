import sys
import os
import time
import socket
import requests
import asyncio
import websockets
from pathlib import Path

# Set PYTHONPATH to project root
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

def print_header(msg):
    print("\n" + "="*60)
    print(f"  {msg}")
    print("="*60)

def check_port(port, name):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('127.0.0.1', port))
        if result == 0:
            print(f"[OK] {name} is listening on port {port}")
            return True
        else:
            print(f"[FAIL] {name} is NOT responding on port {port}")
            return False

def check_imports():
    print_header("Checking Dependencies...")
    libs = ['fastapi', 'sqlalchemy', 'cv2', 'ultralytics', 'easyocr', 'webview', 'websockets']
    for lib in libs:
        try:
            __import__(lib)
            print(f"[OK] {lib} installed")
        except ImportError:
            print(f"[FAIL] {lib} is MISSING. Run 'pip install {lib}'")

async def test_backend():
    print_header("Checking Backend Hub (Port 8001)...")
    try:
        res = requests.get("http://localhost:8001/api/match/all", timeout=5)
        if res.status_code == 200:
            print("[OK] Backend API is reachable")
        else:
            print(f"[FAIL] Backend API returned status {res.status_code}")
    except Exception as e:
        print(f"[FAIL] Could not connect to backend: {e}")

async def test_ai_machine():
    print_header("Checking AI Machine Control (Port 7777)...")
    try:
        res = requests.get("http://localhost:7777/", timeout=5)
        if res.status_code == 200:
            print("[OK] AI Control Panel is reachable")
        else:
            print(f"[FAIL] AI Control Panel returned status {res.status_code}")
    except Exception as e:
        print(f"[FAIL] Could not connect to AI Control Panel: {e}")

def run_diagnostics():
    print_header("FERWAFA SYSTEM DIAGNOSTICS")
    check_imports()
    
    backend_up = check_port(8001, "National Hub")
    ai_up = check_port(7777, "AI Machine")
    
    if backend_up:
        asyncio.run(test_backend())
    
    if ai_up:
        asyncio.run(test_ai_machine())

    print_header("DIAGNOSTICS COMPLETE")
    print("If everything is [OK], your system is ready for use.")
    print("If there are [FAIL] marks, read the error message for the solution.")

if __name__ == "__main__":
    run_diagnostics()
    input("\nPress ENTER to exit...")
