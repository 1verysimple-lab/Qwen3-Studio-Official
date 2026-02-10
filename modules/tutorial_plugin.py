import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import os
import json
import shutil
import sys

def initialize(app):
    """
    Tutorial & Automated Scripting Module.
    Injects the 'Generate Tutorial' feature and manages automated sequences.
    """
    # 1. UI Injection: Inject the button into the Branding Frame (Legacy Location)
    # Uses app.colors and branding frame provided in the main app structure
    tut_row = tk.Frame(app.brand_frame, bg=app.colors["header_bg"])
    tut_row.pack(anchor=tk.W, pady=(5,0))
    
    def start_tutorial_flow():
        """Selected Language Dialog with proper window centering."""
        d = tk.Toplevel(app.root)
        d.title("Select Tutorial Language")
        d.geometry("350x250")
        d.resizable(False, False)
        d.transient(app.root)
        d.grab_set()
        
        try:
            x = app.root.winfo_rootx() + (app.root.winfo_width()//2) - 175
            y = app.root.winfo_rooty() + (app.root.winfo_height()//2) - 125
            d.geometry(f"+{x}+{y}")
        except: pass

        tk.Label(d, text="Tutorial Setup", font=("Segoe UI", 12, "bold"), pady=15).pack()
        tk.Label(d, text="Choose your preferred language:", font=("Segoe UI", 10)).pack(pady=(0, 10))
        
        lang_var = tk.StringVar(value="English")
        opts = ["English", "Spanish", "Chinese"]
        combo = ttk.Combobox(d, textvariable=lang_var, values=opts, state="readonly", width=20)
        combo.pack(pady=5)
        
        def begin():
            language = lang_var.get()
            d.destroy()
            
            # Destination selection - User decides where to create the tutorial folder
            dest_dir = filedialog.askdirectory(title=f"Select Destination for {language} Tutorial Files")
            if not dest_dir: return
            
            execute_tutorial_generation(language, dest_dir)

        tk.Button(d, text="Begin Generation", command=begin, bg=app.colors["accent"], fg="white", 
                  font=("Segoe UI", 10, "bold"), pady=8).pack(fill=tk.X, padx=40, pady=20)

    def execute_tutorial_generation(language, dest_dir):
        """Generates files in chosen folder and LOADS them without auto-running."""
        lang_cfg = {
            "English": ("", "English"),
            "Spanish": ("_ES", "Spanish"),
            "Chinese": ("_CN", "Chinese")
        }
        suffix, model_lang = lang_cfg.get(language, ("", "English"))
        
        # Determine paths relative to the application root
        if getattr(sys, 'frozen', False):
            # Running in a bundle (.exe)
            # Look for tutorials NEXT to the .exe, not inside the temp folder
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running in normal Python environment
            base_dir = os.path.dirname(app.modules_dir)
        source_fname = f"Tutorial_01_Welcome{suffix}.json"
        source_fpath = os.path.join(base_dir, "tutorials", source_fname)
        
        if not os.path.exists(source_fpath):
            messagebox.showerror("Error", f"Source tutorial file not found: {source_fname}")
            return

        try:
            # Create a specific folder in the user's chosen destination
            final_output_path = os.path.join(dest_dir, f"Blues_Tutorial_{language}")
            if not os.path.exists(final_output_path):
                os.makedirs(final_output_path)

            # Copy tutorial JSONs to the new destination for the user to keep
            tutorial_src_dir = os.path.join(base_dir, "tutorials")
            if not os.path.exists(tutorial_src_dir):
                messagebox.showerror("Error", "The 'tutorials/' folder must be in the same directory as the application.")
                return
            shutil.copytree(tutorial_src_dir, final_output_path, dirs_exist_ok=True)

            with open(source_fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Force the correct language for the engine blocks
            for block in data:
                block["language"] = model_lang
            
            # Switch to Batch Tab so user sees the result
            app.notebook.select(app.tab_batch)
            
            # Feed data to director but DO NOT trigger start_scene_generation automatically
            if hasattr(app, 'director'):
                app.director.load_script_data(data, name=f"Tutorial Chapter 1 ({language})")
                # Removed auto-trigger logic per Blues' request
                messagebox.showinfo("Success", f"Tutorial generated in:\n{final_output_path}\n\nChapter 1 loaded in Batch Studio. Press 'Start Batch' when ready.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate tutorial: {e}")

    # Button setup inside the Branding Frame row
    app.btn_tut = tk.Button(tut_row, text="Generate Tutorial", command=start_tutorial_flow, 
                        bg=app.colors["accent"], fg="white", font=("Segoe UI", 8, "bold"), 
                        bd=0, padx=8, pady=2, cursor="hand2")
    app.btn_tut.pack(side=tk.LEFT)