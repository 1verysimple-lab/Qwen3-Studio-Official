import os
import sys
import zipfile
import requests
import shutil
import time
import subprocess
from pathlib import Path
from tqdm import tqdm

# --- 1. CONFIGURATION ---
APP_ZIP_URL = "https://huggingface.co/Bluesed/QWEN_STUDIO/resolve/main/Qwen3Studio_v4.1.0.zip?download=true"
ENGINE_ZIP_URL = "https://huggingface.co/Bluesed/blues-qwen/resolve/main/blues-Qwen3-TTS.zip?download=true"
PATCH_ZIP_URL = "https://huggingface.co/Bluesed/blues-qwen/resolve/main/qwen_tts.zip?download=true"

# --- PATH DEFINITIONS ---
INSTALL_DIR = Path(os.getenv('LOCALAPPDATA')) / "Qwen3Studio"
ENGINE_DIR = INSTALL_DIR / "Qwen3-TTS" 
EXE_NAME = "Qwen3Studio.exe"
ICON_NAME = "pq.ico"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def download_file(url, dest_path, description="File"):
    print(f"\n⬇️  Downloading {description}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 
        
        t = tqdm(total=total_size, unit='iB', unit_scale=True, desc=dest_path.name)
        with open(dest_path, 'wb') as file:
            for data in response.iter_content(block_size):
                t.update(len(data))
                file.write(data)
        t.close()
        return True
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return False

def install_engine_smartly(zip_path, target_root, target_engine_folder):
    """
    Extracts Engine Weights. Flattens structure so base/custom are at root.
    """
    print(f"\n🧠 Installing Weights to {target_engine_folder.name}...")
    if target_engine_folder.exists(): shutil.rmtree(target_engine_folder)
    target_engine_folder.mkdir(parents=True, exist_ok=True)
    
    stage_dir = target_root / "temp_engine_stage"
    if stage_dir.exists(): shutil.rmtree(stage_dir)
    stage_dir.mkdir()
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(stage_dir)
        items = os.listdir(stage_dir)
        if len(items) == 1 and (stage_dir / items[0]).is_dir():
            nested = stage_dir / items[0]
            for item in os.listdir(nested):
                shutil.move(str(nested / item), str(target_engine_folder))
        else:
            for item in items:
                shutil.move(str(stage_dir / item), str(target_engine_folder))
        print("✅ Weights Installed.")
    except Exception as e:
        print(f"❌ Weights Install Failed: {e}")
    finally:
        if stage_dir.exists(): shutil.rmtree(stage_dir)

def install_patch_aggressive(zip_path, target_engine_folder):
    """
    Hunts specifically for 'qwen_tts.py' and moves it to the target root.
    Destroys any wrapper folders.
    """
    print(f"\n🧩 Installing Logic Patch (Aggressive Mode)...")
    try:
        # Extract to a temp folder first
        patch_stage = target_engine_folder / "patch_temp"
        if patch_stage.exists(): shutil.rmtree(patch_stage)
        patch_stage.mkdir()

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(patch_stage)
            
        # HUNT FOR THE FILE
        target_file_name = "qwen_tts.py"
        found = list(patch_stage.rglob(target_file_name))
        
        if found:
            src = found[0]
            dst = target_engine_folder / target_file_name
            print(f"   🎯 Found {target_file_name} inside {src.parent.name}")
            shutil.move(str(src), str(dst))
            print(f"✅ Moved {target_file_name} to Engine root.")
        else:
            print(f"⚠️  CRITICAL: {target_file_name} was not found in the patch zip!")
            
        # Cleanup
        shutil.rmtree(patch_stage)

    except Exception as e:
        print(f"❌ Patch Failed: {e}")

def create_shortcut_safe(target_exe, icon_path):
    desktop = Path(os.getenv('USERPROFILE')) / "Desktop"
    link_path = desktop / "Qwen3 Studio.lnk"
    vbs_script = f"""
    Set oWS = WScript.CreateObject("WScript.Shell")
    Set oLink = oWS.CreateShortcut("{str(link_path)}")
    oLink.TargetPath = "{str(target_exe)}"
    oLink.WorkingDirectory = "{str(target_exe.parent)}"
    oLink.IconLocation = "{str(icon_path)}"
    oLink.Save
    """
    vbs_file = target_exe.parent / "create_shortcut.vbs"
    try:
        with open(vbs_file, "w") as f:
            f.write(vbs_script)
        subprocess.run(["cscript", "//Nologo", str(vbs_file)], check=True)
        os.remove(vbs_file)
        print("✅ Shortcut created successfully.")
    except Exception as e:
        print(f"⚠️  Shortcut creation failed: {e}")

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*60)
    print("   🚀 QWEN3 STUDIO INSTALLER (Aggressive Patch)")
    print("="*60)

    if INSTALL_DIR.exists():
        print(f"🗑️  Cleaning old installation...")
        try:
            shutil.rmtree(INSTALL_DIR)
        except Exception:
            print("⚠️  App is running. Close it and press ENTER.")
            input()
            shutil.rmtree(INSTALL_DIR, ignore_errors=True)

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    # App
    app_zip = INSTALL_DIR / "app.zip"
    if download_file(APP_ZIP_URL, app_zip, "Application"):
        print("📦 Extracting App...")
        with zipfile.ZipFile(app_zip, 'r') as z: z.extractall(INSTALL_DIR)
        os.remove(app_zip)
        nested_app = INSTALL_DIR / "Qwen3Studio"
        if nested_app.exists() and nested_app.is_dir():
            for item in os.listdir(nested_app):
                shutil.move(str(nested_app / item), str(INSTALL_DIR))
            os.rmdir(nested_app)

    # Engine
    engine_zip = INSTALL_DIR / "engine.zip"
    if download_file(ENGINE_ZIP_URL, engine_zip, "Weights"):
        install_engine_smartly(engine_zip, INSTALL_DIR, ENGINE_DIR)
        os.remove(engine_zip)

    # Patch (Aggressive)
    patch_zip = INSTALL_DIR / "patch.zip"
    if download_file(PATCH_ZIP_URL, patch_zip, "Logic"):
        install_patch_aggressive(patch_zip, ENGINE_DIR)
        os.remove(patch_zip)

    # Shortcut
    target_exe = INSTALL_DIR / EXE_NAME
    bundled_icon = Path(resource_path(ICON_NAME))
    dest_icon = INSTALL_DIR / ICON_NAME
    if bundled_icon.exists():
        shutil.copy(bundled_icon, dest_icon)
        if target_exe.exists():
            create_shortcut_safe(target_exe, dest_icon)

    print("\n" + "="*60)
    print("🎉 INSTALLATION COMPLETE!")
    print("   Launch from your Desktop.")
    print("="*60)
    time.sleep(5)

if __name__ == "__main__":
    main()