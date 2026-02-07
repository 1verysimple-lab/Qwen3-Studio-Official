import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import zipfile
import time

# =========================================================================
# ⚙️ CONFIGURATION
# =========================================================================
# The hidden system folder where the heavy engine lives
APP_DATA_ROOT = os.path.join(os.getenv('LOCALAPPDATA'), "Qwen3Studio")
ENGINE_ROOT = os.path.join(APP_DATA_ROOT, "Qwen3-TTS")

# YOUR HUGGING FACE DIRECT LINK
ENGINE_DOWNLOAD_URL = "https://huggingface.co/Bluesed/blues-qwen/resolve/main/blues-Qwen3-TTS.zip?download=true"

class EngineInstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Qwen3 Studio - Setup")
        self.geometry("480x320")
        self.resizable(False, False)
        self.success = False

        # Center window
        self.eval('tk::PlaceWindow . center')
        
        # UI Styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header
        tk.Label(self, text="Installing AI Engine", font=("Segoe UI", 16, "bold")).pack(pady=(25, 10))
        tk.Label(self, text="Downloading high-fidelity models (4.5 GB).\nHosted on Hugging Face High-Speed Servers.", font=("Segoe UI", 10), fg="#555").pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=20)

        # Status Label
        self.status_label = tk.Label(self, text="Initializing...", font=("Segoe UI", 9), fg="#333")
        self.status_label.pack(pady=5)

        # Start Download Thread
        threading.Thread(target=self.start_installation, daemon=True).start()

    def start_installation(self):
        temp_zip = os.path.join(APP_DATA_ROOT, "engine_temp.zip")
        os.makedirs(APP_DATA_ROOT, exist_ok=True)
        
        try:
            self.update_status("Connecting to server...")
            response = requests.get(ENGINE_DOWNLOAD_URL, stream=True)
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
                        # Show GB progress
                        downloaded_gb = downloaded / (1024**3)
                        total_gb = total_size / (1024**3)
                        self.update_status(f"Downloading: {int(percent)}%  ({downloaded_gb:.2f} GB / {total_gb:.2f} GB)")
            
            self.update_status("Extracting (This takes 1-2 mins)...")
            self.progress['mode'] = 'indeterminate'
            self.progress.start(10)
            
            if not zipfile.is_zipfile(temp_zip):
                 raise ValueError("Downloaded file is corrupt.")

            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(APP_DATA_ROOT)
            
            self.update_status("Cleaning up...")
            os.remove(temp_zip)
            
            if os.path.exists(ENGINE_ROOT):
                self.success = True
                self.quit()
            else:
                messagebox.showerror("Structure Error", f"Folder '{ENGINE_ROOT}' not found after extraction.")
                self.quit()

        except Exception as e:
            messagebox.showerror("Installation Error", f"Failed: {str(e)}")
            if os.path.exists(temp_zip):
                try: os.remove(temp_zip)
                except: pass
            self.quit()

    def update_status(self, text):
        self.status_label.config(text=text)

def main():
    # 1. Check if Engine Exists in AppData
    if not os.path.exists(ENGINE_ROOT):
        installer = EngineInstaller()
        installer.mainloop()
        if not installer.success:
            return # User closed window or failed

    # 2. Launch Main App
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