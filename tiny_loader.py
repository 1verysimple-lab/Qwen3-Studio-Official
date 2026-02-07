import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import zipfile
import subprocess
import time

# =========================================================================
# 🔗 CONFIGURATION
# =========================================================================
# The link to your "Payload" (The 2.7GB App)
APP_ZIP_URL = "https://huggingface.co/Bluesed/blues-qwen/resolve/main/Studio_App_v3.8.2.zip?download=true"

# The name of the file INSIDE the zip (The Payload's true name)
APP_EXE_NAME = "Qwen3_Studio_Setup.exe"

# The name of the Shortcut we will create
SHORTCUT_NAME = "Qwen3 Studio"

# Install Destination
INSTALL_DIR = os.path.join(os.getenv('LOCALAPPDATA'), "Qwen3Studio")
APP_PATH = os.path.join(INSTALL_DIR, APP_EXE_NAME)

def create_desktop_shortcut(target_path, shortcut_name):
    """Creates a Windows Shortcut (.lnk) using a temporary VBScript."""
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
        
        # VBScript to create shortcut (No external libraries needed)
        vbs_script = f"""
        Set oWS = WScript.CreateObject("WScript.Shell")
        sLinkFile = "{shortcut_path}"
        Set oLink = oWS.CreateShortcut(sLinkFile)
        oLink.TargetPath = "{target_path}"
        oLink.WorkingDirectory = "{os.path.dirname(target_path)}"
        oLink.Description = "Launch Qwen3 Studio"
        oLink.Save
        """
        
        vbs_file = os.path.join(os.getenv("TEMP"), "make_shortcut.vbs")
        with open(vbs_file, "w") as f:
            f.write(vbs_script)
            
        os.system(f'cscript /nologo "{vbs_file}"')
        os.remove(vbs_file)
        print(f"✅ Shortcut created: {shortcut_path}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to create shortcut: {e}")
        return False

class TinyLoader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Hide window initially
        
        # 1. SMART CHECK: Is it already installed?
        if os.path.exists(APP_PATH):
            print("🚀 App found! Launching directly...")
            subprocess.Popen([APP_PATH])
            sys.exit(0)
            
        # 2. IF NOT INSTALLED: Show the UI
        self.deiconify()
        self.title("Qwen3 Studio - Setup")
        self.geometry("550x380")
        self.resizable(False, False)
        self.eval('tk::PlaceWindow . center')
        
        style = ttk.Style()
        style.theme_use('clam')
        self.configure(bg="#f0f0f0")
        
        # UI Elements
        tk.Label(self, text="Setting up Qwen3 Studio", font=("Segoe UI", 16, "bold"), bg="#f0f0f0").pack(pady=(20, 5))
        tk.Label(self, text="Professional AI Audio Workstation", font=("Segoe UI", 10), fg="#666", bg="#f0f0f0").pack(pady=(0, 20))

        info_frame = tk.Frame(self, bg="white", padx=15, pady=15, relief="sunken", bd=1)
        info_frame.pack(fill="x", padx=30)
        
        warn_msg = (
            "⚠️ IMPORTANT: FIRST TIME SETUP\n\n"
            "1. This process downloads the App Core (2.7 GB).\n"
            "2. When the App launches, it will fetch the AI Engine (4.5 GB).\n"
            "3. Loading AI into VRAM takes time (5-10 minutes).\n\n"
            "Please be patient. Do not close the window if it looks frozen."
        )
        tk.Label(info_frame, text=warn_msg, font=("Segoe UI", 9), justify="left", bg="white", fg="#333").pack(anchor="w")

        self.progress_frame = tk.Frame(self, bg="#f0f0f0")
        self.progress_frame.pack(fill="x", padx=30, pady=20)
        
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal", length=480, mode="determinate")
        self.progress.pack()
        
        self.status_label = tk.Label(self.progress_frame, text="Ready to Install", font=("Segoe UI", 9), bg="#f0f0f0", fg="#555")
        self.status_label.pack(pady=5)

        self.start_btn = ttk.Button(self, text="Start Download & Install", command=self.start_thread)
        self.start_btn.pack(pady=10)

    def start_thread(self):
        self.start_btn.config(state="disabled")
        threading.Thread(target=self.install_sequence, daemon=True).start()

    def install_sequence(self):
        os.makedirs(INSTALL_DIR, exist_ok=True)
        zip_path = os.path.join(INSTALL_DIR, "app_core.zip")
        
        try:
            # 1. DOWNLOAD
            self.update_status("Downloading App Core (2.7 GB)...")
            response = requests.get(APP_ZIP_URL, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024): 
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            perc = (downloaded / total_size) * 100
                            self.progress['value'] = perc
                            self.update_status(f"Downloading: {int(perc)}% ({downloaded//1024//1024} MB)")

            # 2. EXTRACT
            self.update_status("Extracting Application...")
            self.progress['mode'] = 'indeterminate'
            self.progress.start(10)
            
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(INSTALL_DIR)
            
            # 3. CLEANUP
            os.remove(zip_path)
            
            # 4. CREATE SHORTCUT (The New Part)
            self.update_status("Creating Desktop Shortcut...")
            create_desktop_shortcut(APP_PATH, SHORTCUT_NAME)
            
            # 5. LAUNCH
            if os.path.exists(APP_PATH):
                self.update_status("Launching Studio...")
                subprocess.Popen([APP_PATH])
                self.quit()
            else:
                messagebox.showerror("Error", "Installation failed: Executable not found.")
                self.quit()

        except Exception as e:
            messagebox.showerror("Setup Failed", f"Error: {e}")
            self.start_btn.config(state="normal")
            self.progress.stop()

    def update_status(self, text):
        self.status_label.config(text=text)

if __name__ == "__main__":
    app = TinyLoader()
    app.mainloop()