"""
Universal HuggingFace Upload Script (Flash-Proof Edition).
Includes 'input()' pauses so the window doesn't vanish on error.
"""
import os
import sys
import json
import zipfile
import traceback  # Added to catch hidden crashes
from pathlib import Path

# --- HELPER: PAUSE ON EXIT ---
def exit_with_pause(code=0):
    print("\n" + "="*70)
    input("?? Press ENTER to close this window...")
    sys.exit(code)

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("? CRITICAL ERROR: 'huggingface_hub' is not installed!")
    print("   Run: pip install huggingface_hub")
    exit_with_pause(1)

# --- CONFIGURATION LOADING ---
try:
    if not Path("release_config.json").exists():
        print(f"? ERROR: release_config.json not found in: {os.getcwd()}")
        exit_with_pause(1)
        
    with open("release_config.json", "r") as f:
        CONFIG = json.load(f)
except Exception as e:
    print(f"? ERROR reading config: {e}")
    exit_with_pause(1)

VERSION = CONFIG.get("app_version", "4.0")
APP_NAME = CONFIG.get("app_name", "Qwen3Studio")
ZIP_FILENAME = f"{APP_NAME}_v{VERSION}.zip"

def get_hf_token():
    token = os.getenv("HF_TOKEN")
    if not token:
        print("\n? ERROR: HF_TOKEN environment variable is missing.")
        print("   Run: $env:HF_TOKEN=\"hf_your_token_here\" (PowerShell)")
        exit_with_pause(1)
    return token

def zip_application_fast():
    source_dir = Path("dist") / APP_NAME
    output_zip = Path("dist") / ZIP_FILENAME
    
    print("=" * 70)
    print(f"?? PACKAGING VERSION {VERSION} (MODE: STORE/NO-COMPRESS)")
    print("=" * 70)
    
    if not source_dir.exists():
        print(f"? Build folder not found at: {source_dir}")
        print("   Did you run 'pyinstaller Qwen3Studio.spec'?")
        return None

    print(f"  Source: {source_dir}")
    print(f"  Target: {output_zip}")
    
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_STORED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = Path(root) / file
                    archive_name = file_path.relative_to(source_dir.parent)
                    zipf.write(file_path, archive_name)
                    
        print(f"? Packaging Complete: {output_zip.name}")
        return output_zip
        
    except Exception as e:
        print(f"? Packaging Failed: {e}")
        return None

def upload_file_to_hf(file_path, repo_id, repo_type="model"):
    token = get_hf_token()
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"? File not found: {file_path}")
        return False

    file_size_gb = file_path.stat().st_size / (1024 * 1024 * 1024)
    print(f"\n?? UPLOADING: {file_path.name} ({file_size_gb:.2f} GB)")
    print(f"  Destination: {repo_id} ({repo_type})")

    api = HfApi()
    try:
        create_repo(repo_id, repo_type=repo_type, token=token, exist_ok=True)
        api.upload_file(
            path_or_fileobj=str(file_path),
            path_in_repo=file_path.name,
            repo_id=repo_id,
            repo_type=repo_type,
            token=token,
            commit_message=f"Release {APP_NAME} v{VERSION} (Storage Mode)",
        )
        print("? UPLOAD SUCCESSFUL")
        return True
    except Exception as e:
        print(f"? UPLOAD FAILED: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        # Default to 'app' if no args provided (makes double-clicking useful)
        args = sys.argv[1:]
        if not args:
            print("??  No arguments provided. Defaulting to 'app' upload.")
            args = ["app"]

        if "app" in args:
            zip_path = zip_application_fast()
            if zip_path:
                upload_file_to_hf(zip_path, CONFIG["hf_repo_id"], repo_type="model")

        if "engine" in args:
            engine_path = Path(CONFIG["engine_bundle_name"])
            upload_file_to_hf(engine_path, CONFIG["engine_repo_id"], repo_type="model")

        print("\n?? Operation Complete.")
        exit_with_pause(0)

    except Exception:
        traceback.print_exc()
        exit_with_pause(1)