import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import webbrowser
import time

# Try to import huggingface_hub
try:
    from huggingface_hub import snapshot_download
    import huggingface_hub.utils as hf_utils
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

# Forced Paths (Stability)
current_dir = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)

SOX_DIR = os.path.join(current_dir, "sox")
CONFIG_FILE = os.path.join(current_dir, "app_config.json")

MODEL_REPOS = {
    "custom": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "base":   "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
}

class TqdmWrapper:
    """A minimal tqdm-compatible wrapper to pipe progress to Tkinter."""
    def __init__(self, callback, stop_check=None, *args, **kwargs):
        self.callback = callback
        self.stop_check = stop_check
        self.total = kwargs.get('total', 0)
        self.n = 0
        self.start_t = time.time()
        self.desc = kwargs.get('desc', '')
        self.last_update_t = 0

    def update(self, n=1):
        if self.stop_check and self.stop_check():
            raise InterruptedError("Download cancelled by user.")
        
        self.n += n
        curr_t = time.time()
        # Throttle UI updates to 10Hz
        if curr_t - self.last_update_t < 0.1:
            return
        self.last_update_t = curr_t

        elapsed = curr_t - self.start_t
        speed = self.n / elapsed if elapsed > 0 else 0
        remaining = (self.total - self.n) / speed if speed > 0 and self.total else 0
        
        # Format speed
        if speed > 1024*1024:
            speed_str = f"{speed/(1024*1024):.1f} MB/s"
        elif speed > 1024:
            speed_str = f"{speed/1024:.1f} KB/s"
        else:
            speed_str = f"{speed:.0f} B/s"
            
        # Format ETA
        if remaining > 3600:
            eta_str = f"{int(remaining//3600)}h {int((remaining%3600)//60)}m"
        elif remaining > 60:
            eta_str = f"{int(remaining//60)}m {int(remaining%60)}s"
        else:
            eta_str = f"{int(remaining)}s"
            
        if self.callback:
            self.callback(self.n, self.total, speed_str, eta_str, self.desc)

    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass

def get_engine_root():
    """Gets the engine root from config or defaults to local './engine'."""
    engine_root = os.path.join(current_dir, "engine")
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                engine_root = cfg.get("engine_root", engine_root)
        except: pass
    return engine_root

def check_system():
    """Checks if core components are present."""
    # 1. SoX Check
    sox_root = os.path.join(current_dir, "sox")
    internal_sox = os.path.join(current_dir, "_internal", "sox")
    
    sox_ok = os.path.exists(os.path.join(sox_root, "sox.exe")) or \
             os.path.exists(os.path.join(internal_sox, "sox.exe"))
    
    if not sox_ok:
        import shutil
        sox_ok = shutil.which("sox") is not None
    
    # 2. Engine Check
    engine_root = get_engine_root()
    
    # In a frozen (built) app, prioritize the engine folder next to the EXE
    if getattr(sys, 'frozen', False):
        local_engine = os.path.join(os.path.dirname(sys.executable), "engine")
        if os.path.exists(local_engine):
            engine_root = local_engine

    models_found = 0
    for mtype in MODEL_REPOS.keys():
        mpath = os.path.join(engine_root, mtype)
        if os.path.exists(mpath):
            # Check for any of these core model files
            has_files = any(os.path.exists(os.path.join(mpath, f)) for f in ["config.json", "model.safetensors", "pytorch_model.bin"])
            if has_files:
                models_found += 1
            
    # Success if we have SoX and AT LEAST ONE model engine
    return sox_ok, (models_found > 0)

class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Qwen3 Studio - First Run Setup")
        self.geometry("650x600")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)
        
        try:
            icon_path = os.path.join(current_dir, "pq.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except: pass

        self.current_step = 0
        self.is_downloading = False
        self.is_cancelled = False
        
        self.engine_path_var = tk.StringVar(value=get_engine_root())
        self.status_var = tk.StringVar(value="Waiting...")
        self.speed_var = tk.StringVar(value="")
        self.eta_var = tk.StringVar(value="")
        self.metrics_var = tk.StringVar(value="")
        
        self.container = tk.Frame(self, bg="#1e1e1e")
        self.container.pack(fill="both", expand=True, padx=30, pady=30)
        
        self.steps = [
            self.create_welcome_page,
            self.create_security_page,
            self.create_download_page,
            self.create_finish_page
        ]
        
        # Check logic to skip download page if ready
        sox, models = check_system()
        if sox and models:
            self.current_step = 3 # Jump to finish
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.show_step()

    def on_closing(self):
        if self.is_downloading:
            ans = messagebox.askyesnocancel("Download in Progress", 
                "A download is currently active.\n\n"
                "YES: Continue in background (App will launch when done)\n"
                "NO: Stop and exit\n"
                "CANCEL: Stay here")
            if ans is True: # Yes
                self.withdraw()
                # Thread will finish and call self.destroy() at the end
            elif ans is False: # No
                self.is_cancelled = True
                self.status_var.set("Stopping...")
                # Thread will catch is_cancelled and exit
            else: # Cancel
                pass
        else:
            self.destroy()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_step(self):
        self.clear_container()
        self.steps[self.current_step]()

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.show_step()

    # --- PAGES ---

    def create_welcome_page(self):
        tk.Label(self.container, text="Welcome to Qwen3 Studio", font=("Segoe UI", 20, "bold"), bg="#1e1e1e", fg="white").pack(pady=(20, 10))
        tk.Label(self.container, text="The Professional Local AI Audio Suite", font=("Segoe UI", 12), bg="#1e1e1e", fg="#3498db").pack(pady=(0, 30))
        
        msg = "This setup wizard will ensure you have all the necessary components to run Qwen3 Studio.\n\n" \
              "Since this is a high-performance AI application, it requires significant disk space (~15GB) and a modern GPU.\n\n" \
              "Click 'Next' to verify your system configuration."
        
        tk.Label(self.container, text=msg, font=("Segoe UI", 11), bg="#1e1e1e", fg="#cccccc", wraplength=550, justify="left").pack(pady=20)
        
        ttk.Button(self.container, text="Next ➡️", command=self.next_step, width=15).pack(side="bottom", pady=20)

    def create_security_page(self):
        tk.Label(self.container, text="⚠️ Critical Security Notice", font=("Segoe UI", 18, "bold"), bg="#1e1e1e", fg="#e74c3c").pack(pady=(10, 20))
        
        warn_frame = tk.Frame(self.container, bg="#2c0b0e", padx=15, pady=15, bd=1, relief="solid")
        warn_frame.pack(fill="x", pady=10)
        
        tk.Label(warn_frame, text="WINDOWS SMART APP CONTROL", font=("Segoe UI", 12, "bold"), bg="#2c0b0e", fg="#e74c3c").pack(anchor="w")
        
        msg = "Because this software is open-source and not digitally signed with a corporate certificate, Windows may block it by default.\n\n" \
              "1. If you see a 'Smart Screen' popup, click 'More Info' -> 'Run Anyway'.\n" \
              "2. If the app silently fails to launch, you may need to temporarily disable Smart App Control in Windows Settings."
        
        tk.Label(warn_frame, text=msg, font=("Segoe UI", 10), bg="#2c0b0e", fg="white", wraplength=520, justify="left").pack(pady=10)
        
        def open_help():
            webbrowser.open("https://support.microsoft.com/en-us/topic/what-is-smart-app-control-285ea03d-fa88-4d56-aa36-7cee43bb4608")

        link = tk.Label(self.container, text="Click here to read more about Smart App Control", font=("Segoe UI", 10, "underline"), bg="#1e1e1e", fg="#3498db", cursor="hand2")
        link.pack(pady=10)
        link.bind("<Button-1>", lambda e: open_help())

        tk.Label(self.container, text="By clicking Next, you acknowledge you have permissions to run unsigned software.", font=("Segoe UI", 9, "italic"), bg="#1e1e1e", fg="#777").pack(side="bottom", pady=(0,5))
        ttk.Button(self.container, text="I Understand & Agree ➡️", command=self.next_step, width=25).pack(side="bottom", pady=10)

    def create_download_page(self):
        tk.Label(self.container, text="📦 Component Download", font=("Segoe UI", 18, "bold"), bg="#1e1e1e", fg="white").pack(pady=(10, 20))
        
        # Status Box
        status_f = tk.LabelFrame(self.container, text=" Required Assets ", bg="#1e1e1e", fg="#3498db", font=("Segoe UI", 10, "bold"), padx=15, pady=15)
        status_f.pack(fill="x", pady=10)
        
        sox_ok, models_ok = check_system()
        
        def add_row(lbl, ok):
            f = tk.Frame(status_f, bg="#1e1e1e")
            f.pack(fill="x", pady=5)
            tk.Label(f, text=lbl, bg="#1e1e1e", fg="white", width=25, anchor="w").pack(side="left")
            color = "#2ecc71" if ok else "#e74c3c"
            txt = "✅ INSTALLED" if ok else "❌ MISSING"
            tk.Label(f, text=txt, bg="#1e1e1e", fg=color, font=("Segoe UI", 9, "bold")).pack(side="right")

        add_row("Audio Engine (SoX):", sox_ok)
        add_row("AI Models (~15GB):", models_ok)
        
        # Path Selection
        tk.Label(self.container, text="Install Location for Models:", bg="#1e1e1e", fg="#aaa", font=("Segoe UI", 9)).pack(anchor="w", pady=(20, 5))
        path_f = tk.Frame(self.container, bg="#1e1e1e")
        path_f.pack(fill="x")
        
        e_path = ttk.Entry(path_f, textvariable=self.engine_path_var)
        e_path.pack(side="left", fill="x", expand=True)
        
        def browse():
            from tkinter import filedialog
            d = filedialog.askdirectory()
            if d: self.engine_path_var.set(d)
        
        ttk.Button(path_f, text="Browse...", command=browse, width=8).pack(side="left", padx=5)

        # --- PROGRESS UI ---
        self.prog_frame = tk.Frame(self.container, bg="#1e1e1e")
        self.prog_frame.pack(fill="x", pady=20)
        
        self.progress = ttk.Progressbar(self.prog_frame, mode="determinate")
        self.progress.pack(fill="x", pady=5)
        
        metrics_f = tk.Frame(self.prog_frame, bg="#1e1e1e")
        metrics_f.pack(fill="x")
        
        tk.Label(metrics_f, textvariable=self.metrics_var, bg="#1e1e1e", fg="#ccc", font=("Segoe UI", 9)).pack(side="left")
        tk.Label(metrics_f, textvariable=self.speed_var, bg="#1e1e1e", fg="#3498db", font=("Segoe UI", 9, "bold")).pack(side="right")
        
        self.lbl_eta = tk.Label(self.prog_frame, textvariable=self.eta_var, bg="#1e1e1e", fg="#f1c40f", font=("Segoe UI", 9))
        self.lbl_eta.pack(pady=2)

        # Download Logic
        self.dl_btn = ttk.Button(self.container, text="⬇️ Download All (15GB)", command=self.start_download)
        self.dl_btn.pack(side="bottom", pady=10, fill="x")
        
        self.cancel_btn = ttk.Button(self.container, text="✖️ Cancel Download", command=self.cancel_download, state="disabled")
        self.cancel_btn.pack(side="bottom", pady=5, fill="x")
        
        self.lbl_status = tk.Label(self.container, textvariable=self.status_var, bg="#1e1e1e", fg="#f1c40f", font=("Segoe UI", 10))
        self.lbl_status.pack(side="bottom", pady=5)

        if models_ok and sox_ok:
            self.status_var.set("All components found.")
            self.dl_btn.config(text="Next ➡️", command=self.next_step)
            self.prog_frame.pack_forget()

    def cancel_download(self):
        if messagebox.askyesno("Cancel", "Stop downloading and exit?"):
            self.is_cancelled = True
            self.status_var.set("Cancelling...")

    def update_progress(self, n, total, speed, eta, desc):
        def _update():
            if total:
                self.progress["maximum"] = total
                self.progress["value"] = n
                # Metrics
                mb_n = n / (1024*1024)
                mb_tot = total / (1024*1024)
                if mb_tot > 1024:
                    self.metrics_var.set(f"{mb_n/1024:.2f} GB / {mb_tot/1024:.2f} GB")
                else:
                    self.metrics_var.set(f"{mb_n:.1f} MB / {mb_tot:.1f} MB")
            
            self.speed_var.set(speed)
            self.eta_var.set(f"Estimated Time: {eta}")
            if desc:
                # Clean up desc if it's a long path
                short_desc = desc.split("/")[-1][:30]
                self.status_var.set(f"Fetching: {short_desc}...")
        
        self.after(0, _update)

    def start_download(self):
        if not HF_AVAILABLE:
            messagebox.showerror("Error", "huggingface_hub library is missing.")
            return
            
        target_root = self.engine_path_var.get()
        if not os.path.exists(target_root):
            try:
                os.makedirs(target_root, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create folder: {e}")
                return

        # Save config immediately
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: cfg = json.load(f)
            except: pass
        cfg["engine_root"] = target_root
        try:
            with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f, indent=4)
        except: pass

        self.dl_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.status_var.set("Initializing download... please wait.")
        self.is_downloading = True
        self.is_cancelled = False
        
        def worker():
            # Patch tqdm
            original_tqdm = hf_utils.tqdm
            def patched_tqdm(*args, **kwargs):
                return TqdmWrapper(self.update_progress, lambda: self.is_cancelled, *args, **kwargs)
            hf_utils.tqdm = patched_tqdm
            
            try:
                for mtype, repo in MODEL_REPOS.items():
                    if self.is_cancelled: break
                    target = os.path.join(target_root, mtype)
                    if not os.path.exists(os.path.join(target, "config.json")):
                        self.after(0, lambda m=mtype: self.status_var.set(f"Downloading {m} engine..."))
                        snapshot_download(repo_id=repo, local_dir=target)
                
                if self.is_cancelled:
                    self.after(0, lambda: self.status_var.set("Download Cancelled."))
                else:
                    self.after(0, lambda: [
                        self.status_var.set("Download Complete!"),
                        self.dl_btn.config(state="normal", text="Next ➡️", command=self.next_step),
                        self.cancel_btn.config(state="disabled")
                    ])
            except Exception as e:
                if "cancelled" in str(e).lower() or isinstance(e, InterruptedError):
                    self.after(0, lambda: self.status_var.set("Download Cancelled."))
                else:
                    self.after(0, lambda: [
                        self.status_var.set("Download Failed."),
                        messagebox.showerror("Error", f"Download failed: {e}"),
                        self.dl_btn.config(state="normal")
                    ])
            finally:
                hf_utils.tqdm = original_tqdm
                self.is_downloading = False
                self.after(0, self.destroy) # Always destroy so mainloop returns
        
        threading.Thread(target=worker, daemon=True).start()

    def create_finish_page(self):
        tk.Label(self.container, text="🎉 Ready to Launch", font=("Segoe UI", 20, "bold"), bg="#1e1e1e", fg="#2ecc71").pack(pady=(30, 20))
        
        info = "Configuration complete. You are ready to start directing."
        tk.Label(self.container, text=info, font=("Segoe UI", 12), bg="#1e1e1e", fg="white").pack()
        
        note_frame = tk.Frame(self.container, bg="#2b2b2b", padx=15, pady=15, bd=1, relief="sunken")
        note_frame.pack(fill="x", pady=30)
        
        tk.Label(note_frame, text="NOTE ON FIRST LAUNCH:", font=("Segoe UI", 10, "bold"), bg="#2b2b2b", fg="#f1c40f").pack(anchor="w")
        note = "The first time you run the app, it will take 1-2 minutes to compile shaders and load the AI models into VRAM.\n\n" \
               "Please be patient and do not close the window if it looks 'frozen' for a moment."
        tk.Label(note_frame, text=note, font=("Segoe UI", 10), bg="#2b2b2b", fg="#ccc", wraplength=500, justify="left").pack(pady=5)
        
        ttk.Button(self.container, text="🚀 LAUNCH STUDIO", command=self.destroy, width=20).pack(side="bottom", pady=20)

def ensure_system():
    sox_ok, models_ok = check_system()
    if not sox_ok or not models_ok:
        app = SetupWizard()
        app.mainloop()
        sox_ok, models_ok = check_system()
        if not sox_ok or not models_ok:
            sys.exit(0) # Exit if not setup
    return True

if __name__ == "__main__":
    ensure_system()