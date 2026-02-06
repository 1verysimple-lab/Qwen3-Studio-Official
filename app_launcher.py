import os
import sys
import subprocess
import requests
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import time
import tempfile

# --- CONFIGURATION ---
REPO_URL = "https://huggingface.co/Qwen/Qwen2.5-Audio-Instruct/resolve/main"
# IMPORTANT: This JSON file on GitHub dictates if an update is needed
VERSION_URL = "https://raw.githubusercontent.com/1verysimple-lab/Qwen3-TTS/main/version.json"

REQUIRED_FILES = ["model.safetensors", "config.json", "tokenizer.json", "preprocessor_config.json"]

if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.path.join(ROOT_DIR, "Qwen3-TTS")
MAIN_EXE = os.path.join(ROOT_DIR, "app_main.exe")

class LauncherUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Qwen3 Studio Launcher")
        self.root.geometry("450x320")
        self.root.configure(bg="#1e1e1e")
        self.center_window(450, 320)

        try: self.root.iconbitmap(os.path.join(ROOT_DIR, "pq.ico"))
        except: pass

        # UI Elements
        tk.Label(self.root, text="Qwen3 Studio", font=("Segoe UI", 16, "bold"), fg="white", bg="#1e1e1e").pack(pady=(20, 5))
        
        self.lbl_status = tk.Label(self.root, text="Initializing...", font=("Segoe UI", 10), fg="#aaaaaa", bg="#1e1e1e")
        self.lbl_status.pack(pady=5)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=350, mode="determinate")
        self.progress.pack(pady=20)

        # Action Button
        self.btn_action = tk.Button(self.root, text="Wait...", state="disabled", command=self.launch_app, 
                                    bg="#2980b9", fg="white", font=("Segoe UI", 11, "bold"), width=20, relief="flat")
        self.btn_action.pack(pady=20)

        # Start Logic
        threading.Thread(target=self.startup_sequence, daemon=True).start()
        self.root.mainloop()

    def center_window(self, w, h):
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

    def update_ui(self, status=None, progress=None, btn_text=None, btn_state=None, btn_cmd=None, color=None):
        """Thread-safe UI updater"""
        self.root.after(0, lambda: self._apply_ui(status, progress, btn_text, btn_state, btn_cmd, color))

    def _apply_ui(self, status, progress, btn_text, btn_state, btn_cmd, color):
        if status: self.lbl_status.config(text=status)
        if progress is not None: self.progress['value'] = progress
        if btn_text: self.btn_action.config(text=btn_text)
        if btn_state: self.btn_action.config(state=btn_state)
        if btn_cmd: self.btn_action.config(command=btn_cmd)
        if color: self.btn_action.config(bg=color)

    def startup_sequence(self):
        # 1. CHECK UPDATES
        self.update_ui("Checking for updates...", 10)
        if self.check_updates():
            return # Pause here if update found

        # 2. VERIFY FILES
        self.update_ui("Verifying AI Models...", 30)
        if not self.verify_models():
            self.download_models()
        
        # 3. LAUNCH
        self.update_ui("Ready", 100, "Launch Studio", "normal", self.launch_app, "#27ae60")
        time.sleep(1)
        self.launch_app()

    def check_updates(self):
        try:
            # Get Local Version
            local_ver = "0.0.0"
            ver_file = os.path.join(ROOT_DIR, "version.json")
            if os.path.exists(ver_file):
                with open(ver_file, 'r') as f:
                    local_ver = json.load(f).get("version", "0.0.0")

            # Get Remote Version
            response = requests.get(VERSION_URL, timeout=3)
            if response.status_code == 200:
                data = response.json()
                remote_ver = data.get("version", "0.0.0")
                download_url = data.get("download_url", "")

                if remote_ver != local_ver:
                    self.update_ui(
                        f"Update Available: v{remote_ver}", 
                        0, 
                        "Download & Update", 
                        "normal", 
                        lambda: threading.Thread(target=self.perform_update, args=(download_url,), daemon=True).start(),
                        "#e67e22"
                    )
                    return True
        except Exception as e:
            print(f"Update check failed: {e}")
        return False

    def perform_update(self, url):
        """Downloads the new installer and runs it"""
        try:
            self.update_ui("Initializing Download...", 0, "Downloading...", "disabled")
            
            # Create temp path for the installer
            installer_path = os.path.join(tempfile.gettempdir(), "Qwen3_Studio_Update.exe")
            
            # Stream Download
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(installer_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            self.update_ui(f"Downloading Update... {int(percent)}%", percent)

            self.update_ui("Launching Installer...", 100)
            
            # Run the installer and exit launcher
            subprocess.Popen([installer_path])
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to download update.\n{e}")
            self.update_ui("Update Failed", 0, "Retry", "normal", lambda: threading.Thread(target=self.perform_update, args=(url,), daemon=True).start())

    def verify_models(self):
        if not os.path.exists(MODEL_DIR): return False
        for f in REQUIRED_FILES:
            if not os.path.exists(os.path.join(MODEL_DIR, f)): return False
        return True

    def download_models(self):
        if not os.path.exists(MODEL_DIR): os.makedirs(MODEL_DIR)
        self.update_ui("Downloading AI Models...", 0, "Downloading...", "disabled")
        
        total_files = len(REQUIRED_FILES)
        for idx, filename in enumerate(REQUIRED_FILES):
            dest = os.path.join(MODEL_DIR, filename)
            if os.path.exists(dest): continue

            url = f"{REPO_URL}/{filename}?download=true"
            self.update_ui(f"Downloading {filename} ({idx+1}/{total_files})", (idx / total_files) * 100)

            try:
                r = requests.get(url, stream=True)
                total = int(r.headers.get('content-length', 0))
                with open(dest, 'wb') as f:
                    down = 0
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                        down += len(chunk)
                        if total > 0:
                            f_prog = (down / total) * (100 / total_files)
                            base = (idx / total_files) * 100
                            self.update_ui(None, base + f_prog)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download {filename}\n{e}")
                sys.exit()

    def launch_app(self):
        self.update_ui("Launching Studio...", 100)
        if os.path.exists(MAIN_EXE):
            subprocess.Popen([MAIN_EXE], cwd=ROOT_DIR)
            self.root.destroy()
        elif os.path.exists("app_main.py"):
            subprocess.Popen(["python", "app_main.py"], cwd=ROOT_DIR)
            self.root.destroy()

if __name__ == "__main__":
    LauncherUI()