"""Script to package Phase 7 release candidate."""
import os
import zipfile
import shutil
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent

def build_zip():
    zip_path = repo_root / "code.zip"
    if zip_path.exists():
        zip_path.unlink()
        
    code_dir = repo_root / "code"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(code_dir):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
                
            for file in files:
                if file.endswith(".pyc"):
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(repo_root)
                z.write(file_path, arcname)
                print(f"Added {arcname}")
                
    print(f"Created {zip_path.name} ({zip_path.stat().st_size} bytes)")

def lock_output():
    src = repo_root / "outputs" / "output.csv"
    dst = repo_root / "output.csv"
    if src.exists():
        shutil.copy2(src, dst)
        print(f"Copied output.csv to repo root.")
    else:
        print("outputs/output.csv not found!")

def clarify_log():
    log_path = repo_root / "log.txt"
    message = (
        "\\n--- PHASE 7 CLARIFICATION ---\\n"
        "This repository-root log.txt is NOT the official transcript. "
        "The official orchestration transcript is maintained at "
        "%USERPROFILE%\\\\hackerrank_orchestrate_august26\\\\log.txt "
        "per the project rules. This file remains only for structure compliance.\\n"
    )
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(message)
    print("Updated repo-root log.txt with clarification.")

if __name__ == "__main__":
    print("Building Phase 7 Release Candidate...")
    lock_output()
    clarify_log()
    build_zip()
    print("Release Candidate build complete.")
