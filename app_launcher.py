import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import zipfile
import time
import shutil

# =========================================================================
# ⚙️ CONFIGURATION
# =========================================================================
# The hidden system folder where the heavy engine lives
APP_DATA_ROOT = os.path.join(os.getenv('LOCALAPPDATA'), "Qwen3Studio")
ENGINE_ROOT = os.path.join(APP_DATA_ROOT, "Qwen3-TTS")

# YOUR HUGGING FACE DIRECT LINK
ENGINE_DOWNLOAD_URL = "https://huggingface.co/Bluesed/blues-qwen/resolve/main/blues-Qwen3-TTS.zip?download=true"

# UPDATE MANIFEST URL
VERSION_URL = "https://raw.githubusercontent.com/1verysimple-lab/Qwen3-Studio-Official/main/version.json"
LOCAL_VERSION_FILE = "version.txt"

class EngineInstaller(tk.Tk):
    def __init__(self, mode="full", download_url=None, target_version=None):
        super().__init__()
        self.mode = mode
        self.download_url = download_url or ENGINE_DOWNLOAD_URL
        self.target_version = target_version
        
        self.title("Qwen3 Studio - Update Manager" if mode == "patch" else "Qwen3 Studio - Setup")
        self.geometry("480x320")
        self.resizable(False, False)
        self.success = False

        # Center window
        self.eval('tk::PlaceWindow . center')
        
        # UI Styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header
        header_text = "Installing Updates" if mode == "patch" else "Installing AI Engine"
        tk.Label(self, text=header_text, font=("Segoe UI", 16, "bold")).pack(pady=(25, 10))
        
        desc_text = f"Downloading patch for version {target_version}." if mode == "patch" else "Downloading high-fidelity models (4.5 GB).\nHosted on Hugging Face High-Speed Servers."
        tk.Label(self, text=desc_text, font=("Segoe UI", 10), fg="#555").pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=20)

        # Status Label
        self.status_label = tk.Label(self, text="Initializing...", font=("Segoe UI", 9), fg="#333")
        self.status_label.pack(pady=5)

        # Start Download Thread
        threading.Thread(target=self.start_installation, daemon=True).start()

    def start_installation(self):
        temp_zip = os.path.join(APP_DATA_ROOT, "update_temp.zip" if self.mode == "patch" else "engine_temp.zip")
        os.makedirs(APP_DATA_ROOT, exist_ok=True)
        
        try:
            self.update_status("Connecting to server...")
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024 # 1MB chunks
            downloaded = 0

            with open(temp_zip, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        self.progress['value'] = percent
                        
                        if self.mode == "patch":
                            self.update_status(f"Downloading Patch: {int(percent)}% ({downloaded//1024} KB / {total_size//1024} KB)")
                        else:
                            downloaded_gb = downloaded / (1024**3)
                            total_gb = total_size / (1024**3)
                            self.update_status(f"Downloading: {int(percent)}%  ({downloaded_gb:.2f} GB / {total_gb:.2f} GB)")
            
            self.update_status("Applying Patch..." if self.mode == "patch" else "Extracting (This takes 1-2 mins)...")
            self.progress['mode'] = 'indeterminate'
            self.progress.start(10)
            
            if not zipfile.is_zipfile(temp_zip):
                 raise ValueError("Downloaded file is corrupt.")

            # Target directory: Patch goes to current dir, Full goes to APP_DATA_ROOT
            extract_path = os.getcwd() if self.mode == "patch" else APP_DATA_ROOT
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            self.update_status("Finalizing...")
            os.remove(temp_zip)
            
            # Update local version file if successful
            if self.mode == "patch" and self.target_version:
                with open(LOCAL_VERSION_FILE, "w") as f:
                    f.write(self.target_version)
            
            messagebox.showinfo("Installation Complete", "Qwen3 Studio Engine installed successfully!")
            self.success = True
            self.quit()

        except Exception as e:
            messagebox.showerror("Update Error" if self.mode == "patch" else "Installation Error", f"Failed: {str(e)}")
            if os.path.exists(temp_zip):
                try: os.remove(temp_zip)
                except: pass
            self.quit()

    def update_status(self, text):
        self.status_label.config(text=text)

def version_to_tuple(v):
    return tuple(map(int, (v.split("."))))

def check_for_updates():
    """Checks GitHub for version.json and handles patching or full update prompts."""
    # 1. Read local version
    local_version = "4.6.0"  # <--- THE FIX (Hardcode the truth)
    if os.path.exists(LOCAL_VERSION_FILE):
        try:
            with open(LOCAL_VERSION_FILE, "r") as f:
                ver_from_file = f.read().strip()
                if ver_from_file: local_version = ver_from_file
        except: pass
    
    try:
        # 2. Fetch Remote Manifest
        response = requests.get(VERSION_URL, timeout=5)
        response.raise_for_status()
        manifest = response.json()
        
        remote_version = manifest.get("current_version", "0.0.0")
        
        if local_version == remote_version:
            return # Up to date
            
        # 3. Decision Tree using tuple comparison
        v_local = version_to_tuple(local_version)
        v_remote = version_to_tuple(remote_version)
        
        # Major Gap: First number mismatch
        if v_remote[0] > v_local[0]:
            msg = f"A major update (v{remote_version}) is available.\n\nPlease download the full application from:\n{manifest.get('full_url')}"
            messagebox.showinfo("Major Update Available", msg)
            return

        # Small Gap: Minor or Patch mismatch
        if v_remote > v_local:
            if messagebox.askyesno("Update Available", f"A new patch (v{remote_version}) is available. Install now?"):
                patcher = EngineInstaller(mode="patch", download_url=manifest.get("patch_url"), target_version=remote_version)
                patcher.mainloop()
                
    except Exception as e:
        print(f"Update check failed (Offline mode): {e}")
        # Default to launching local version

def main():
    # 0. Extract embedded tutorials folder if running as a frozen executable
    if getattr(sys, 'frozen', False):
        try:
            # Source is inside the MEIPASS (temp folder where PyInstaller extracts its bundled files)
            embedded_tutorials_src = os.path.join(sys._MEIPASS, 'tutorials')
            # Destination is next to the executable
            target_tutorials_dest = os.path.join(os.path.dirname(sys.executable), 'tutorials')

            if os.path.exists(embedded_tutorials_src) and not os.path.exists(target_tutorials_dest):
                shutil.copytree(embedded_tutorials_src, target_tutorials_dest, dirs_exist_ok=True)
        except Exception as e:
            # Log or print the error for debugging, but don't stop the launch
            print(f"Error extracting embedded tutorials: {e}")
            pass

    # 1. Check if Engine Exists in AppData
    if not os.path.exists(ENGINE_ROOT):
        installer = EngineInstaller(mode="full")
        installer.mainloop()
        if not installer.success:
            return # User closed window or failed

    # 2. Check for Updates
    check_for_updates()

    # 3. Launch Main App
    try:
        # We import app_main only AFTER the engine is confirmed
        import app_main
        
        # Launch logic
        if hasattr(app_main, 'launch_studio'):
            app_main.launch_studio()
        elif hasattr(app_main, 'main'):
            app_main.main()
        else:
            messagebox.showerror("Error", "Could not find 'launch_studio' in app_main.py")
            
    except Exception as e:
        messagebox.showerror("Crash", f"App failed to launch: {e}")

if __name__ == "__main__":
    main()