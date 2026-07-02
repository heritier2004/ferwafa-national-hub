import os
import shutil
from pathlib import Path

def main():
    root = Path(r"c:\Users\User\Documents\NEW_VERSION")
    backup_dir = root / "backups" / "pre_prod_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = [
        root / "football_intelligence.db",
        root / ".env",
        root / "package.json",
        root / "ai_machine" / "ai_machine_config.json",
        root / "ai_machine_desktop" / "package.json"
    ]
    
    print("Starting Pre-Production Backup...")
    for f in files_to_backup:
        if f.exists():
            dest = backup_dir / f.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            print(f"Backed up: {f.relative_to(root)} -> {dest.relative_to(root)}")
        else:
            print(f"Warning: File not found for backup: {f.relative_to(root)}")
            
    print("Backup complete!")

if __name__ == "__main__":
    main()
