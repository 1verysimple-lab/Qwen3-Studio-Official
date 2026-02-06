import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import os
import time
import json

# --- CONSTANTS ---
PRESETS = [
    "Vivian", "Serena", "Ryan", "Aiden", "Eric", 
    "Dylan", "Uncle_Fu", "Ono_Anna", "Sohee"
]
SUPPORTED_LANGUAGES = [
    "English", "Chinese", "Japanese", "Korean", "Cantonese", 
    "German", "French", "Russian", "Portuguese", "Spanish", 
    "Italian", "Auto"
]

# --- COLORS & STYLES ---
STATUS_COLORS = {
    "pending": "#95a5a6",   # Grey
    "queued":  "#f39c12",   # Orange
    "busy":    "#3498db",   # Blue
    "review":  "#f1c40f",   # Yellow (Review)
    "success": "#2ecc71",   # Green
    "failed":  "#e74c3c"    # Red
}

class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 500
        self.wraplength = 180
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, wraplength=self.wraplength, font=("Segoe UI", 8))
        label.pack(ipadx=4, ipady=4)

    def hidetip(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None

class ScriptBlock(tk.Frame):
    """
    Represents a single line of dialogue in the scene.
    """
    def __init__(self, parent, index, delete_callback, available_speakers, available_styles, app_ref, block_type="standard"):
        super().__init__(parent, bg="white", pady=5, padx=5, bd=1, relief="solid")
        self.index = index
        self.delete_callback = delete_callback
        self.app = app_ref
        self.block_type = block_type
        self.generated_audio = None
        self.sample_rate = 24000
        self.status = "pending"
        
        # --- UI LAYOUT ---
        # Engine Indicator Strip (Left side)
        self.engine_strip = tk.Frame(self, width=6, bg="#bdc3c7")
        self.engine_strip.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # Top Row: Controls
        top_f = tk.Frame(self, bg="white")
        top_f.pack(fill=tk.X, pady=(0, 5))
        
        # Status Indicator
        self.status_light = tk.Canvas(top_f, width=24, height=24, bg="white", highlightthickness=0, cursor="hand2")
        self.status_light.pack(side=tk.LEFT, padx=(0, 5))
        self.draw_status_icon("pending")
        self.status_light.bind("<Button-1>", self.toggle_manual_status)
        self.status_light.bind("<Button-3>", self.reject_status)
        ToolTip(self.status_light, "L-Click: Approve (Green)\nR-Click: Reject (Red)\nYellow = Review")
        
        # Speaker Selector
        tk.Label(top_f, text="Speaker:", bg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.speaker_var = tk.StringVar()
        
        # Values depend on type
        spk_values = available_speakers if block_type == "standard" else self.app.voice_configs.keys()
        
        self.cb_speaker = ttk.Combobox(top_f, textvariable=self.speaker_var, values=list(spk_values), state="readonly", width=15)
        self.cb_speaker.pack(side=tk.LEFT, padx=5)
        self.cb_speaker.bind("<<ComboboxSelected>>", self.update_engine_indicator)
        if list(spk_values): self.cb_speaker.current(0)
        
        # Style Selector (Only for Standard)
        self.style_var = tk.StringVar()
        self.lbl_style = tk.Label(top_f, text="Style:", bg="white", font=("Segoe UI", 8))
        self.cb_style = ttk.Combobox(top_f, textvariable=self.style_var, values=available_styles, state="readonly", width=15)
        
        if block_type == "standard":
            self.lbl_style.pack(side=tk.LEFT)
            self.cb_style.pack(side=tk.LEFT, padx=5)
        
        # Language Selector
        tk.Label(top_f, text="Lang:", bg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="English")
        self.cb_lang = ttk.Combobox(top_f, textvariable=self.lang_var, values=SUPPORTED_LANGUAGES, state="readonly", width=8)
        self.cb_lang.pack(side=tk.LEFT, padx=5)

        # Precision Sliders
        tk.Label(top_f, text="T:", bg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.temp_var = tk.DoubleVar(value=0.8)
        self.lbl_temp = tk.Label(top_f, text="0.8", bg="white", font=("Consolas", 8), width=3)
        self.sc_temp = ttk.Scale(top_f, from_=0.1, to=1.5, variable=self.temp_var, orient=tk.HORIZONTAL, length=60)
        self.sc_temp.pack(side=tk.LEFT, padx=2)
        self.lbl_temp.pack(side=tk.LEFT)
        
        tk.Label(top_f, text="P:", bg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(5, 0))
        self.top_p_var = tk.DoubleVar(value=0.8)
        self.lbl_p = tk.Label(top_f, text="0.8", bg="white", font=("Consolas", 8), width=3)
        self.sc_p = ttk.Scale(top_f, from_=0.1, to=1.0, variable=self.top_p_var, orient=tk.HORIZONTAL, length=60)
        self.sc_p.pack(side=tk.LEFT, padx=2)
        self.lbl_p.pack(side=tk.LEFT)

        # Setup Traces for labels
        self.temp_var.trace_add("write", lambda *a: self.lbl_temp.config(text=f"{self.temp_var.get():.1f}"))
        self.top_p_var.trace_add("write", lambda *a: self.lbl_p.config(text=f"{self.top_p_var.get():.1f}"))

        # Delete Button
        tk.Button(top_f, text="✕", command=lambda: self.delete_callback(self), 
                  bg="white", fg="#e74c3c", bd=0, cursor="hand2", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)

        # Text Input
        self.text_input = tk.Text(self, height=3, width=60, font=("Segoe UI", 10), wrap=tk.WORD, bg="#f8f9fa")
        self.text_input.pack(fill=tk.X)
        self.text_input.bind("<KeyRelease>", self.update_word_count)
        
        # Bottom Row
        bot_f = tk.Frame(self, bg="white")
        bot_f.pack(fill=tk.X, pady=(5, 0))
        
        self.lbl_word_count = tk.Label(bot_f, text="0 words", bg="white", fg="grey", font=("Segoe UI", 8))
        self.lbl_word_count.pack(side=tk.LEFT)
        
        self.btn_play = ttk.Button(bot_f, text="▶ Play", command=self.play_audio, state=tk.DISABLED, width=8)
        self.btn_play.pack(side=tk.RIGHT)
        
        self.btn_stop = ttk.Button(bot_f, text="⏹", command=self.stop_audio, state=tk.DISABLED, width=4)
        self.btn_stop.pack(side=tk.RIGHT, padx=2)
        
        self.chk_retry_var = tk.BooleanVar(value=True)
        
        self.update_engine_indicator()

    def update_engine_indicator(self, event=None, load_defaults=True):
        spk = self.speaker_var.get()
        
        if self.block_type == "clone":
            self.engine_strip.config(bg="#8e44ad") # Purple
            ToolTip(self.engine_strip, "Engine: Voice Clone")
            
            # Load Profile Precision Defaults
            if load_defaults:
                profile = self.app.voice_configs.get(spk)
                if profile:
                    if "temp" in profile: self.temp_var.set(profile["temp"])
                    if "top_p" in profile: self.top_p_var.set(profile["top_p"])
            return

        if spk in PRESETS:
            self.engine_strip.config(bg="#2ecc71") # Green
            ToolTip(self.engine_strip, "Engine: Custom Voice")
        else:
            self.engine_strip.config(bg="#3498db") # Blue
            ToolTip(self.engine_strip, "Engine: Voice Design")
            
            # Load Design Profile Precision Defaults
            if load_defaults:
                profile = self.app.design_profiles.get(spk)
                if profile:
                    if "temp" in profile: self.temp_var.set(profile["temp"])
                    if "top_p" in profile: self.top_p_var.set(profile["top_p"])

    def draw_status_icon(self, status):
        self.status_light.delete("all")
        w, h = 24, 24
        
        if status == "success":
            # Green Check
            self.status_light.create_oval(2, 2, 22, 22, fill=STATUS_COLORS["success"], outline="")
            self.status_light.create_text(12, 12, text="✔", fill="white", font=("Arial", 12, "bold"))
        elif status == "review":
            # Yellow Question
            self.status_light.create_oval(2, 2, 22, 22, fill=STATUS_COLORS["review"], outline="")
            self.status_light.create_text(12, 12, text="?", fill="black", font=("Arial", 12, "bold"))
        elif status == "failed":
            # Red Exclamation
            self.status_light.create_oval(2, 2, 22, 22, fill=STATUS_COLORS["failed"], outline="")
            self.status_light.create_text(12, 12, text="!", fill="white", font=("Arial", 12, "bold"))
        elif status == "busy":
            # Blue Spinner-ish
            self.status_light.create_oval(2, 2, 22, 22, fill=STATUS_COLORS["busy"], outline="")
            self.status_light.create_text(12, 12, text="⏳", fill="white", font=("Arial", 10))
        else:
            # Pending / Grey
            self.status_light.create_oval(2, 2, 22, 22, fill=STATUS_COLORS["pending"], outline="#bdc3c7")
            self.status_light.create_text(12, 12, text="•", fill="white", font=("Arial", 10, "bold"))

    def set_status(self, status):
        self.status = status
        self.draw_status_icon(status)
        
        if status in ["success", "review"]:
            if self.generated_audio is not None:
                self.btn_play.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.NORMAL)
            self.chk_retry_var.set(False) 
        elif status == "failed":
            self.chk_retry_var.set(True) 
            if self.generated_audio is None:
                self.btn_play.config(state=tk.DISABLED)
                self.btn_stop.config(state=tk.DISABLED)
        elif status == "busy":
             self.btn_play.config(state=tk.DISABLED)
             self.btn_stop.config(state=tk.DISABLED)

    def toggle_manual_status(self, event=None):
        if self.status == "busy" or self.status == "queued": return
        
        if self.status == "review":
            self.set_status("success") # Approve
        elif self.status == "success":
            self.set_status("failed") # Reject
        elif self.status == "failed":
            self.set_status("success") # Force Approve
        else: # pending
            self.set_status("success")

    def reject_status(self, event=None):
        if self.status in ["busy", "queued"]: return
        self.set_status("failed")

    def sync_status_from_checkbox(self):
        # Deprecated logic kept for safety if needed
        pass

    def update_word_count(self, event=None):
        text = self.text_input.get("1.0", tk.END).strip()
        count = len(text.split())
        self.lbl_word_count.config(text=f"{count} words")
        
        # Safety Warning
        if count > 35:
            self.lbl_word_count.config(fg="#e74c3c", text=f"{count} words (Risk of instability!)")
        else:
            self.lbl_word_count.config(fg="grey")

    def play_audio(self):
        if self.generated_audio is not None:
            sd.stop()
            sd.play(self.generated_audio, self.sample_rate)

    def stop_audio(self):
        sd.stop()

class BatchDirector(tk.Frame):
    def __init__(self, parent, app_reference):
        super().__init__(parent, bg="#f0f0f0")
        self.app = app_reference
        self.blocks = []
        self.script_name_var = tk.StringVar(value="New Script")
        
        # --- TOP TOOLBAR ---
        toolbar = tk.Frame(self, bg="#dfe6e9", padx=10, pady=10)
        toolbar.pack(fill=tk.X)
        
        ttk.Button(toolbar, text="➕ Add Block", command=self.add_block).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="➕ Clone Block", command=self.add_clone_block).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑 Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        
        # Script Load/Save
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(toolbar, text="💾 Save Script", command=self.save_script).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📂 Load Script", command=self.load_script).pack(side=tk.LEFT, padx=2)

        # Script Name Indicator
        tk.Label(toolbar, text="📄", bg="#dfe6e9", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(15, 0))
        tk.Label(toolbar, textvariable=self.script_name_var, bg="#dfe6e9", font=("Segoe UI", 10, "bold"), fg="#2c3e50").pack(side=tk.LEFT)

        # Export Controls
        exp_frame = tk.Frame(toolbar, bg="#dfe6e9")
        exp_frame.pack(side=tk.RIGHT)
        ttk.Button(exp_frame, text="📁 Export Clips", command=self.export_clips).pack(side=tk.LEFT, padx=2)
        ttk.Button(exp_frame, text="🎵 Render Scene", command=self.render_full_scene).pack(side=tk.LEFT, padx=2)

        # --- MAIN SPLIT CONTAINER ---
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#f0f0f0", sashwidth=4)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # 1. Left Frame: Script Blocks
        self.left_frame = tk.Frame(self.paned, bg="#f4f6f9")
        self.paned.add(self.left_frame, minsize=400, stretch="always")

        # Scrollable Canvas for blocks
        self.canvas = tk.Canvas(self.left_frame, bg="#f4f6f9", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg="#f4f6f9")

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # 2. Right Frame: Tools & Style Manager
        self.right_frame = tk.Frame(self.paned, bg="white", width=150)
        self.paned.add(self.right_frame, minsize=130, stretch="never")
        
        self.setup_right_panel()

        # --- BOTTOM ACTION BAR ---
        action_bar = tk.Frame(self, bg="#2c3e50", padx=15, pady=15)
        action_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.btn_run = tk.Button(
            action_bar, text="🎬 RUN SCENE", 
            command=self.start_scene_generation,
            bg="#2ecc71", fg="white", font=("Segoe UI", 12, "bold"), 
            bd=0, padx=20, pady=5, cursor="hand2"
        )
        self.btn_run.pack(side=tk.RIGHT)
        
        # Auto-Switch Checkbox
        self.auto_switch_var = tk.BooleanVar(value=False)
        self.chk_auto_switch = tk.Checkbutton(action_bar, text="⚡ Auto-Switch Engines", variable=self.auto_switch_var,
                                              bg="#2c3e50", fg="white", font=("Segoe UI", 10),
                                              selectcolor="#2c3e50", activebackground="#2c3e50", activeforeground="white")
        self.chk_auto_switch.pack(side=tk.RIGHT, padx=15)
        
        # Play All / Stop Controls
        self.btn_stop_scene = tk.Button(action_bar, text="⏹", command=self.stop_scene, bg="#e74c3c", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=5, cursor="hand2")
        self.btn_stop_scene.pack(side=tk.RIGHT, padx=2)

        self.btn_play_scene = tk.Button(action_bar, text="▶ Play All", command=self.play_scene, bg="#3498db", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=5, cursor="hand2")
        self.btn_play_scene.pack(side=tk.RIGHT, padx=2)
        
        self.lbl_progress = tk.Label(action_bar, text="Ready", bg="#2c3e50", fg="white", font=("Segoe UI", 10))
        self.lbl_progress.pack(side=tk.LEFT)

        # Initial Block
        self.add_block()

    def setup_right_panel(self):
        """Builds the Style Manager on the right side."""
        pad = 10
        tk.Label(self.right_frame, text="Style Manager", font=("Segoe UI", 11, "bold"), bg="white").pack(pady=(15, 5))
        
        f = tk.Frame(self.right_frame, bg="white", padx=pad)
        f.pack(fill=tk.X)
        
        # Style List (Listbox or Combo)
        tk.Label(f, text="Edit Style:", bg="white", anchor="w").pack(fill=tk.X)
        self.sm_style_var = tk.StringVar()
        self.sm_combo = ttk.Combobox(f, textvariable=self.sm_style_var, state="readonly")
        self.sm_combo.pack(fill=tk.X, pady=(0, 10))
        self.sm_combo.bind("<<ComboboxSelected>>", self.on_sm_select)
        
        # Input Fields
        tk.Label(f, text="Name:", bg="white", anchor="w").pack(fill=tk.X)
        self.sm_name_entry = ttk.Entry(f, width=20)
        self.sm_name_entry.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(f, text="Instruction:", bg="white", anchor="w").pack(fill=tk.X)
        self.sm_instr_entry = tk.Text(f, height=5, width=20, font=("Segoe UI", 9), wrap=tk.WORD, bg="#f8f9fa")
        self.sm_instr_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Buttons
        btn_f = tk.Frame(f, bg="white")
        btn_f.pack(fill=tk.X)
        ttk.Button(btn_f, text="💾 Save/Update", command=self.sm_save).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_f, text="🗑 Delete", command=self.sm_delete).pack(fill=tk.X)

        self.refresh_sm_list()

    def refresh_sm_list(self):
        styles = self.get_styles()
        self.sm_combo['values'] = styles
        
        # Update Main App & Blocks
        if hasattr(self.app, 'update_style_combo'):
            self.app.update_style_combo()
            
        for b in self.blocks:
            current = b.style_var.get()
            b.cb_style['values'] = styles
            # If current style was deleted, it stays as text in var but won't be in values.
            # That's acceptable.

    def on_sm_select(self, event):
        name = self.sm_style_var.get()
        instr = self.app.app_config.get("style_instructions", {}).get(name, "")
        
        self.sm_name_entry.delete(0, tk.END)
        self.sm_name_entry.insert(0, name)
        
        self.sm_instr_entry.delete("1.0", tk.END)
        self.sm_instr_entry.insert("1.0", instr)

    def sm_save(self):
        name = self.sm_name_entry.get().strip()
        instr = self.sm_instr_entry.get("1.0", tk.END).strip()
        
        if not name or not instr:
            messagebox.showwarning("Error", "Name and Instruction required.")
            return
            
        self.app.app_config["style_instructions"][name] = instr
        self.app.save_app_config()
        self.refresh_sm_list()
        self.sm_style_var.set(name)
        messagebox.showinfo("Saved", f"Style '{name}' updated.")

    def sm_delete(self):
        name = self.sm_name_entry.get().strip()
        if name in self.app.app_config.get("style_instructions", {}):
            if messagebox.askyesno("Confirm", f"Delete style '{name}'?"):
                del self.app.app_config["style_instructions"][name]
                self.app.save_app_config()
                self.refresh_sm_list()
                self.sm_name_entry.delete(0, tk.END)
                self.sm_instr_entry.delete("1.0", tk.END)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def get_speakers(self):
        # Combines Built-in Presets + Saved Design Profiles
        # Clones are excluded as they require a different model structure
        # Add Design Profiles (Design Mode)
        designs = list(self.app.design_profiles.keys())
        
        return PRESETS + ["---"] + designs

    def get_styles(self):
        return sorted(list(self.app.app_config.get("style_instructions", {}).keys()))

    def get_clone_profiles(self):
        return sorted(list(self.app.voice_configs.keys()))

    def add_clone_block(self):
        self.add_block("clone")

    def add_block(self, block_type="standard"):
        speakers = self.get_speakers()
        styles = self.get_styles()
        
        block = ScriptBlock(self.scroll_frame, len(self.blocks), self.remove_block, speakers, styles, self.app, block_type=block_type)
        block.pack(fill=tk.X, pady=5, padx=10)
        self.blocks.append(block)
        
        # Scroll to bottom
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1)
        return block # Return ref

    def remove_block(self, block_ref):
        block_ref.destroy()
        if block_ref in self.blocks:
            self.blocks.remove(block_ref)

    def clear_all(self):
        if messagebox.askyesno("Clear Scene", "Remove all blocks?"):
            for b in self.blocks:
                b.destroy()
            self.blocks = []
            self.add_block()

    def save_script(self):
        """Saves current blocks to JSON."""
        data = []
        for b in self.blocks:
            data.append({
                "type": b.block_type,
                "speaker": b.speaker_var.get(),
                "style": b.style_var.get(),
                "language": b.lang_var.get(),
                "text": b.text_input.get("1.0", tk.END).strip(),
                "temp": b.temp_var.get(),
                "top_p": b.top_p_var.get()
            })
            
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Scripts", "*.json")])
        if f:
            try:
                with open(f, 'w', encoding='utf-8') as file:
                    json.dump(data, file, indent=2)
                self.script_name_var.set(os.path.basename(f))
                messagebox.showinfo("Saved", f"Script saved to {os.path.basename(f)}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def load_script(self):
        """Loads blocks from JSON."""
        f = filedialog.askopenfilename(filetypes=[("JSON Scripts", "*.json")])
        if not f: return
        
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            if not isinstance(data, list): raise Exception("Invalid format")
            
            self.load_script_data(data, name=os.path.basename(f))
            messagebox.showinfo("Loaded", f"Loaded {len(data)} blocks.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load script:\n{e}")

    def load_script_data(self, data, name="Custom Script"):
        """Programmatically loads blocks from a list of dicts."""
        if not isinstance(data, list): return
        
        # Clear existing
        for b in self.blocks: b.destroy()
        self.blocks = []
        self.script_name_var.set(name)
        
        available_styles = self.get_styles()
        
        for item in data:
            b = self.add_block(item.get("type", item.get("block_type", "standard"))) # support both keys
            b.speaker_var.set(item.get("speaker", ""))
            b.text_input.insert("1.0", item.get("text", ""))
            
            if "temp" in item: b.temp_var.set(item["temp"])
            if "top_p" in item: b.top_p_var.set(item["top_p"])
            if "language" in item: b.lang_var.set(item["language"])
            
            # Check Style availability
            st = item.get("style", "")
            if st and st not in available_styles:
                st = "---"
            b.style_var.set(st)
            
            # Update visual indicator
            b.update_engine_indicator(load_defaults=False)

    def start_scene_generation(self):
        """Main Loop: Iterates through blocks and generates audio."""
        if not self.app.model:
            messagebox.showerror("Error", "Model not loaded!")
            return

        # 1. Filter Pending Blocks
        pending_blocks = []
        for b in self.blocks:
            # Skip if success/review (unless retry is checked)
            if b.status in ["success", "review"] and not b.chk_retry_var.get():
                continue
            pending_blocks.append(b)
        
        if not pending_blocks:
            self.lbl_progress.config(text="Nothing to generate (All blocks accepted).")
            # If auto-switch is on, treat RUN as a Play shortcut if everything is ready
            if self.auto_switch_var.get():
                self.play_scene()
            return

        # 2. Sort Queue for Optimized Switching
        custom_tasks = []
        design_tasks = []
        clone_tasks = []
        
        for b in pending_blocks:
            if b.block_type == "clone":
                clone_tasks.append(b)
            elif b.speaker_var.get() in PRESETS:
                custom_tasks.append(b)
            else:
                design_tasks.append(b) # Assumes design profile

        # Sort Clone tasks by speaker for prompt caching efficiency
        clone_tasks.sort(key=lambda x: x.speaker_var.get())

        # Determine Order based on current engine
        current = self.app.current_model_type
        if current == "base":
            final_queue = clone_tasks + custom_tasks + design_tasks
        elif current == "design":
            final_queue = design_tasks + custom_tasks + clone_tasks
        else: # custom or None
            final_queue = custom_tasks + design_tasks + clone_tasks

        self.app.set_busy(True, "Directing Scene...")
        self.btn_run.config(state=tk.DISABLED)
        
        threading.Thread(target=self._generation_worker, args=(final_queue,), daemon=True).start()

    def retry_marked_blocks(self):
        # Deprecated: functionality moved to main run button
        self.start_scene_generation()

    def _generation_worker(self, queue):
        total = len(queue)
        
        # State for Clone Prompt Caching
        current_clone_speaker = None
        cached_prompt = None

        for i, block in enumerate(queue):
            if self.app.cancel_signal.is_set(): break
            
            text = block.text_input.get("1.0", tk.END).strip()
            speaker_selection = block.speaker_var.get()
            lang = block.lang_var.get()
            
            if not text:
                self.app.root.after(0, lambda b=block: b.set_status("failed"))
                continue

            # --- SMART SWITCHING LOGIC ---
            if block.block_type == "clone":
                required_mode = "base"
            elif speaker_selection in PRESETS:
                required_mode = "custom"
            else:
                required_mode = "design"
            
            if self.app.current_model_type != required_mode:
                # 1. Determine if we should switch
                should_switch = self.auto_switch_var.get()
                
                if not should_switch:
                    # Ask User for Confirmation (Thread-Safe)
                    user_response = [None]
                    def ask_switch():
                        msg = f"Finished all tasks for {self.app.current_model_type.upper()}.\n\n" \
                              f"Switch to {required_mode.upper()} engine to continue?\n" \
                              f"(Click No to stay on current engine)"
                        user_response[0] = messagebox.askyesno("Switch Engine", msg)
                    
                    self.app.root.after(0, ask_switch)
                    
                    # Wait for user input
                    while user_response[0] is None:
                        if self.app.cancel_signal.is_set(): break
                        time.sleep(0.1)
                    
                    if user_response[0]:
                        should_switch = True
                
                if not should_switch or self.app.cancel_signal.is_set():
                    self.app.root.after(0, lambda: self.lbl_progress.config(text="Batch Paused (Engine Switch Cancelled)"))
                    break # Stop processing

                # 2. Perform Switch
                msg = f"Switching to {required_mode.upper()} engine... (Please Wait)"
                self.app.root.after(0, lambda m=msg: self.lbl_progress.config(text=m))
                
                try:
                    self.app.switch_model(required_mode)
                    
                    # 3. Wait for Switch to Complete (since switch_model is threaded)
                    timeout = 90 # seconds
                    start_wait = time.time()
                    while self.app.current_model_type != required_mode or self.app.model is None:
                        if self.app.cancel_signal.is_set(): break
                        if time.time() - start_wait > timeout: 
                            raise Exception("Model load timed out.")
                        time.sleep(0.5)
                    
                    # 4. Stabilization Period
                    time.sleep(1) 
                        
                except Exception as e:
                    print(f"Failed to switch model: {e}")
                    self.app.root.after(0, lambda b=block: b.set_status("failed"))
                    break

            # Update UI from thread
            self.app.root.after(0, lambda b=block: b.set_status("busy"))
            self.app.root.after(0, lambda idx=i+1: self.lbl_progress.config(text=f"Generating block {idx}/{total}..."))
            
            style_name = block.style_var.get()
            temp = block.temp_var.get()
            top_p = block.top_p_var.get()
            instruction = self.app.app_config.get("style_instructions", {}).get(style_name, "")
            
            try:
                wavs = None
                sr = 24000

                if required_mode == "custom":
                    # PRESET (Custom Voice)
                    wavs, sr = self.app.model.generate_custom_voice(
                        text=text,
                        speaker=speaker_selection,
                        instruct=instruction,
                        language=lang,
                        temperature=temp, top_p=top_p
                    )

                elif required_mode == "design":
                    # DESIGN PROFILE (Voice Design)
                    profile = self.app.design_profiles.get(speaker_selection)
                    
                    # Fallback to recipes if not in profiles
                    if not profile and hasattr(self.app, 'voice_recipes'):
                        profile = self.app.voice_recipes.get(speaker_selection)

                    if not profile:
                        raise Exception(f"Profile '{speaker_selection}' not found")

                    desc = profile.get("desc", "")
                    prof_instruct = profile.get("instruct", "")
                    
                    final_instruct = prof_instruct
                    if instruction: 
                        final_instruct = f"{instruction}. {prof_instruct}"
                    
                    wavs, sr = self.app.model.generate_voice_design(
                        text=text,
                        voice_description=desc,
                        instruct=final_instruct,
                        language=lang,
                        temperature=temp, top_p=top_p
                    )
                
                elif required_mode == "base":
                    # VOICE CLONE (Base Model)
                    # Check if we need to generate a new prompt
                    if speaker_selection != current_clone_speaker:
                        self.app.root.after(0, lambda: self.lbl_progress.config(text=f"Locking Voice: {speaker_selection}..."))
                        
                        profile_data = self.app.voice_configs.get(speaker_selection)
                        if not profile_data: raise Exception("Profile not found")
                        
                        audio_path = profile_data.get("audio_path")
                        ref_txt = profile_data.get("transcript")
                        
                        if not audio_path or not os.path.exists(audio_path):
                            raise Exception("Source audio missing")
                            
                        # Create prompt
                        cached_prompt = self.app.model.create_voice_clone_prompt(
                            ref_audio=audio_path,
                            ref_text=ref_txt
                        )
                        current_clone_speaker = speaker_selection
                    
                    # Generate using cached prompt
                    wavs, sr = self.app.model.generate_voice_clone(
                        text=text,
                        language=lang,
                        voice_clone_prompt=cached_prompt,
                        temperature=temp, top_p=top_p
                    )

                # Store Result
                if wavs:
                    block.generated_audio = wavs[0]
                    block.sample_rate = sr
                    self.app.root.after(0, lambda b=block: b.set_status("review"))
                    
                    # Auto-Save to Session History
                    try:
                        ts = time.strftime("%Y%m%d-%H%M%S")
                        safe_spk = "".join(x for x in speaker_selection if x.isalnum())
                        safe_txt = "".join(x for x in text[:15] if x.isalnum())
                        fname = f"{ts}_Batch_{safe_spk}_{safe_txt}.wav"
                        path = os.path.join(self.app.temp_dir, fname)
                        
                        sf.write(path, wavs[0], sr)
                        
                        # Refresh Main History UI
                        if hasattr(self.app, 'refresh_history_list'):
                            self.app.root.after(0, self.app.refresh_history_list)
                    except Exception as e:
                        print(f"Failed to save history: {e}")

                else:
                    raise Exception("No audio returned")

            except Exception as e:
                print(f"Block failed: {e}")
                self.app.root.after(0, lambda b=block: b.set_status("failed"))
        
        def on_complete():
            self.app.set_busy(False)
            self.btn_run.config(state=tk.NORMAL)
            self.lbl_progress.config(text="Scene Complete")
            if self.auto_switch_var.get():
                self.play_scene()
        
        self.app.root.after(0, on_complete)

    def play_scene(self):
        """Concatenates and plays the full scene audio."""
        audio_segments = []
        valid_sr = 24000
        
        for b in self.blocks:
            if b.generated_audio is not None:
                audio_segments.append(b.generated_audio)
                valid_sr = b.sample_rate
                # Add a small silence gap
                silence = np.zeros(int(valid_sr * 0.2)) 
                audio_segments.append(silence)
        
        if not audio_segments:
            messagebox.showinfo("Info", "No audio to play.")
            return
            
        full_audio = np.concatenate(audio_segments)
        sd.stop()
        sd.play(full_audio, valid_sr)

    def stop_scene(self):
        sd.stop()

    def render_full_scene(self):
        """Concatenates all successful audio blocks into one WAV."""
        audio_segments = []
        valid_sr = 24000
        
        for b in self.blocks:
            if b.status == "success" and b.generated_audio is not None:
                audio_segments.append(b.generated_audio)
                valid_sr = b.sample_rate
                # Add a small silence gap? (Optional, e.g. 0.2s)
                silence = np.zeros(int(valid_sr * 0.2)) 
                audio_segments.append(silence)
        
        if not audio_segments:
            messagebox.showwarning("Empty", "No audio generated yet.")
            return
            
        full_audio = np.concatenate(audio_segments)
        
        dst = filedialog.asksaveasfilename(defaultextension=".wav", title="Save Full Scene")
        if dst:
            sf.write(dst, full_audio, valid_sr)
            
            # Auto-Save copy to Session History
            try:
                ts = time.strftime("%Y%m%d-%H%M%S")
                fname = f"{ts}_Full_Scene_Render.wav"
                hist_path = os.path.join(self.app.temp_dir, fname)
                sf.write(hist_path, full_audio, valid_sr)
                
                if hasattr(self.app, 'refresh_history_list'):
                    self.app.refresh_history_list()
            except Exception as e:
                print(f"Failed to save render to history: {e}")

            messagebox.showinfo("Export", "Scene rendered successfully.")

    def export_clips(self):
        """Exports individual files to a folder."""
        folder = filedialog.askdirectory(title="Select Export Folder")
        if not folder: return
        
        count = 0
        pad_len = len(str(len(self.blocks))) # For zero padding 01, 02..
        
        for i, b in enumerate(self.blocks):
            if b.status == "success" and b.generated_audio is not None:
                # Naming: 01_Speaker_First3Words.wav
                txt_slug = "".join(e for e in b.text_input.get("1.0", tk.END)[:15] if e.isalnum())
                fname = f"{str(i+1).zfill(pad_len)}_{b.speaker_var.get()}_{txt_slug}.wav"
                
                path = os.path.join(folder, fname)
                sf.write(path, b.generated_audio, b.sample_rate)
                count += 1
                
        messagebox.showinfo("Export", f"Exported {count} clips.")
