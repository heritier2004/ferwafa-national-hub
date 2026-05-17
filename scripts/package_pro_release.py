import os
import zipfile
import shutil

def package_pro_release():
    print("==================================================")
    print("   FERWAFA AI PITCH MACHINE - PRO PACKAGER")
    print("==================================================")
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ai_dir = os.path.join(root_dir, "ai_machine")
    dist_dir = os.path.join(root_dir, "backend", "dist")
    
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
        
    zip_path = os.path.join(dist_dir, "ai_machine_universal.zip")
    
    print(f"[*] Packaging AI Machine from: {ai_dir}")
    print(f"[*] Target Release: {zip_path}")
    
    # Files to include
    include_patterns = [
        "main.py",
        "processor.py",
        "jersey_detector.py",
        "event_extractor.py",
        "config.py",
        "setup_wizard.py",
        "check_hardware.py",
        "create_desktop_icon.py",
        "install_and_launch.bat",
        "install_and_launch.sh",
        "requirements.txt",
        "assets/",
        "ui/"
    ]
    
    exclude_dirs = [".venv", "__pycache__", "output", "test_videos"]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ai_dir):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, ai_dir)
                
                # Check if it matches include pattern (simple basename or folder check)
                should_include = False
                for pattern in include_patterns:
                    if pattern.endswith("/") and relative_path.startswith(pattern):
                        should_include = True; break
                    if relative_path == pattern:
                        should_include = True; break
                
                if should_include:
                    zipf.write(file_path, relative_path)
                    print(f"  + Added: {relative_path}")
                    
    print("--------------------------------------------------")
    print(f">>> SUCCESS: Pro Release built at {zip_path}")
    print("==================================================")

if __name__ == "__main__":
    package_pro_release()
