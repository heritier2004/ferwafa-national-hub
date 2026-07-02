import os
import zipfile
import shutil
from pathlib import Path

def package_ai_machine():
    print("===================================================")
    print("  [PACKAGE] AI PITCH MACHINE - RELEASE PACKAGER")
    print("===================================================")

    # Paths
    root_dir = Path(__file__).resolve().parent.parent
    ai_machine_dir = root_dir / "ai_machine"
    dist_dir = root_dir / "backend" / "dist"
    output_filename = dist_dir / "ai_machine_universal.zip"

    # 1. Create dist dir
    if not dist_dir.exists():
        dist_dir.mkdir(parents=True)
        print(f"[INFO] Created directory: {dist_dir}")

    # 2. Exclude list
    exclude_patterns = [
        "__pycache__",
        ".venv",
        ".git",
        ".ipynb_checkpoints",
        ".pyc",
        ".DS_Store",
        "temp_",
        "output_",
        ".mp4",
        ".avi",
        "tests" # Exclude tests from production release
    ]

    print(f"[INFO] Packaging {ai_machine_dir}...")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ai_machine_dir):
            # Apply directory exclusions
            dirs[:] = [d for d in dirs if d not in exclude_patterns]
            
            for file in files:
                # Apply file exclusions
                if any(ext in file for ext in exclude_patterns):
                    continue
                if file.endswith('.mp4') or file.endswith('.avi'):
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, ai_machine_dir.parent)
                
                zipf.write(abs_path, rel_path)
                # print(f"  + {rel_path}")

    print(f"\n[SUCCESS] Release baked to {output_filename}")
    print(f"   Size: {os.path.getsize(output_filename) / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    package_ai_machine()
