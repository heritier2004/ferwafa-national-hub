import subprocess
import time
import sys
import webbrowser

def run_system():
    print("National Football Intelligence System - SINGLE-PORT MODE")
    print("---------------------------------------------------------")
    
    print("[1/1] Launching Unified Server (Port 8001)...")
    server = subprocess.Popen([sys.executable, "-m", "backend.app.main"])
    
    time.sleep(3) # Give server a moment
    
    url = "http://127.0.0.1:8001"
    print("\n---------------------------------------------------------")
    print("SYSTEM IS FULLY OPERATIONAL!")
    print(f"Opening system at: {url}")
    print("---------------------------------------------------------")
    print("\nPress CTRL+C in this window to stop the system.")
    
    # Automatically open the browser
    webbrowser.open(url)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping system...")
        server.terminate()
        print("Goodbye!")

if __name__ == "__main__":
    run_system()
