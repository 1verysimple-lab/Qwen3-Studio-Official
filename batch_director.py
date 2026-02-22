import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import random
import gc
import os
import time
import json
import shutil
import torch
import difflib
import tempfile

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

def _deep_destroy_model(app):
    """
    Aggressively destroy the loaded model and free VRAM.
    Deletes internal HF model and processor before dropping the wrapper reference
    so the CUDA allocator can reclaim pages as soon as flush_vram() runs.
    Call this from any background thread that needs to sever the model.
    """
    m = getattr(app, 'model', None)
    if m is not None:
        try:
            if hasattr(m, 'model'):
                del m.model
        except Exception:
            pass
        try:
            if hasattr(m, 'processor'):
                del m.processor
        except Exception:
            pass
        try:
            del m
        except Exception:
            pass
        app.model = None
    app.flush_vram()


def detect_long_pauses(audio_data, sample_rate, max_pause_seconds=2.0):
    """Scans audio array for RMS drops indicating unnatural silences."""
    if audio_data is None:
        return False, "No audio data."
    chunk_length = int(sample_rate * 0.1)  # 100ms chunks
    threshold = 0.005
    consecutive_silent_chunks = 0
    max_allowed_chunks = int(max_pause_seconds / 0.1)
    for i in range(0, len(audio_data), chunk_length):
        chunk = audio_data[i:i + chunk_length]
        rms = np.sqrt(np.mean(chunk ** 2))
        if rms < threshold:
            consecutive_silent_chunks += 1
            if consecutive_silent_chunks > max_allowed_chunks:
                return False, f"Failed: Unnatural pause detected (>{max_pause_seconds}s)."
        else:
            consecutive_silent_chunks = 0
    return True, "Passed"


def verify_transcription(target_text, whisper_transcription):
    """Fuzzy-matches Whisper's output against the script text."""
    clean_target = ''.join(e for e in target_text if e.isalnum() or e.isspace()).lower()
    clean_actual = ''.join(e for e in whisper_transcription if e.isalnum() or e.isspace()).lower()
    similarity = difflib.SequenceMatcher(None, clean_target, clean_actual).ratio()
    if similarity < 0.75:
        return False, f"Low accuracy ({similarity:.2f}). Possible hallucination or garbled speech."
    return True, "Passed"


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
    def __init__(self, parent, index, delete_callback, generate_callback, available_speakers, available_styles, app_ref, block_type="standard", block_number=None):
        super().__init__(parent, bg="white", pady=5, padx=5, bd=1, relief="solid")
        self.index = index
        self.block_number = block_number
        self.delete_callback = delete_callback
        self.generate_callback = generate_callback
        self.app = app_ref
        self.block_type = block_type
        self.generated_audio = None
        self.sample_rate = 24000
        self.status = "pending"
        self.is_collapsed = False

        # --- UI LAYOUT ---
        # Engine Indicator Strip (Left side)
        self.engine_strip = tk.Frame(self, width=6, bg="#bdc3c7")
        self.engine_strip.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # ── COLLAPSED BAR (shown when collapsed) ─────────────────────────────
        self.collapsed_bar = tk.Frame(self, bg="white")
        # Not packed by default — only shown in collapsed state

        self.lbl_num_col = tk.Label(self.collapsed_bar, text=f"#{self.block_number}" if self.block_number else "",
                                    bg="white", fg="#bdc3c7", font=("Consolas", 7, "bold"), width=3, anchor="e")
        self.lbl_num_col.pack(side=tk.LEFT, padx=(0, 3))

        self.status_light_col = tk.Canvas(self.collapsed_bar, width=16, height=16,
                                          bg="white", highlightthickness=0, cursor="hand2")
        self.status_light_col.pack(side=tk.LEFT, padx=(0, 5))
        self.status_light_col.bind("<Button-1>", self.toggle_manual_status)
        self.status_light_col.bind("<Button-3>", self.reject_status)
        ToolTip(self.status_light_col, "L-Click: Approve (Green)\nR-Click: Reject (Red)\nYellow = Review")

        self.lbl_col_speaker = tk.Label(self.collapsed_bar, text="", bg="white",
                                        fg="#444", font=("Segoe UI", 8, "bold"), anchor="w")
        self.lbl_col_speaker.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_col_preview = tk.Label(self.collapsed_bar, text="", bg="white",
                                        fg="#888", font=("Segoe UI", 8, "italic"), anchor="w")
        self.lbl_col_preview.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(self.collapsed_bar, text="▼", command=self.toggle_collapse,
                  bg="white", fg="#7f8c8d", bd=0, cursor="hand2",
                  font=("Arial", 8, "bold")).pack(side=tk.RIGHT, padx=(4, 0))
        # ─────────────────────────────────────────────────────────────────────

        # ── EXPANDED CONTENT ─────────────────────────────────────────────────
        self.expanded_content = tk.Frame(self, bg="white")
        self.expanded_content.pack(fill=tk.X)

        # Top Row: Controls
        top_f = tk.Frame(self.expanded_content, bg="white")
        top_f.pack(fill=tk.X, pady=(0, 5))

        # Block number badge
        self.lbl_num = tk.Label(top_f, text=f"#{self.block_number}" if self.block_number else "",
                                bg="white", fg="#bdc3c7", font=("Consolas", 8, "bold"), width=3, anchor="e")
        self.lbl_num.pack(side=tk.LEFT, padx=(0, 2))

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

        spk_values = available_speakers if block_type == "standard" else self.app.voice_configs.keys()

        self.cb_speaker = ttk.Combobox(top_f, textvariable=self.speaker_var, values=list(spk_values), state="readonly", width=15)
        self.cb_speaker.pack(side=tk.LEFT, padx=5)
        self.cb_speaker.bind("<<ComboboxSelected>>", self._on_speaker_changed)
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
        self.lbl_temp.pack(side=tk.LEFT, padx=(2, 10))

        tk.Label(top_f, text="P:", bg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(5, 0))
        self.top_p_var = tk.DoubleVar(value=0.8)
        self.lbl_p = tk.Label(top_f, text="0.8", bg="white", font=("Consolas", 8), width=3)
        self.sc_p = ttk.Scale(top_f, from_=0.1, to=1.0, variable=self.top_p_var, orient=tk.HORIZONTAL, length=60)
        self.sc_p.pack(side=tk.LEFT, padx=2)
        self.lbl_p.pack(side=tk.LEFT, padx=(2, 10))

        tk.Label(top_f, text="Seed:", bg="white", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(6, 0))
        self.seed_var = tk.StringVar(value="")
        self.seed_entry = ttk.Entry(top_f, textvariable=self.seed_var, width=9, font=("Consolas", 8))
        self.seed_entry.pack(side=tk.LEFT, padx=(2, 10))
        ToolTip(self.seed_entry,
            "Seed — controls reproducibility.\n"
            "Empty = a new random seed is chosen at generation time\n"
            "and written back here so you can replay the exact take.\n"
            "Enter a number to lock in a specific result.")

        # Setup Traces for labels
        self.temp_var.trace_add("write", lambda *a: self.lbl_temp.config(text=f"{self.temp_var.get():.1f}"))
        self.top_p_var.trace_add("write", lambda *a: self.lbl_p.config(text=f"{self.top_p_var.get():.1f}"))

        # Collapse Button (▲ collapse, inside expanded top row)
        tk.Button(top_f, text="▲", command=self.toggle_collapse,
                  bg="white", fg="#7f8c8d", bd=0, cursor="hand2",
                  font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=(0, 2))

        # Delete Button
        tk.Button(top_f, text="✕", command=lambda: self.delete_callback(self),
                  bg="white", fg="#e74c3c", bd=0, cursor="hand2", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)

        # Text Input
        self.text_input = tk.Text(self.expanded_content, height=3, width=60, font=("Segoe UI", 10), wrap=tk.WORD, bg="#f8f9fa")
        self.text_input.pack(fill=tk.X)
        self.text_input.bind("<KeyRelease>", self.update_word_count)

        # Bottom Row
        self.bot_f = tk.Frame(self.expanded_content, bg="white")
        self.bot_f.pack(fill=tk.X, pady=(5, 5))

        self.lbl_word_count = tk.Label(self.bot_f, text="0 words", bg="white", fg="grey", font=("Segoe UI", 8))
        self.lbl_word_count.pack(side=tk.LEFT)

        self.btn_play = ttk.Button(self.bot_f, text="▶ Play", command=self.play_audio, state=tk.DISABLED, width=8, style="Flat.TButton")
        self.btn_play.pack(side=tk.RIGHT)

        self.btn_stop = ttk.Button(self.bot_f, text="⏹", command=self.stop_audio, state=tk.DISABLED, width=4, style="Flat.TButton")
        self.btn_stop.pack(side=tk.RIGHT, padx=2)

        self.btn_multi_gen = ttk.Button(self.bot_f, text="🎲 x3", command=lambda: self.app.director.generate_multi_takes(self), width=5, style="Flat.TButton")
        self.btn_multi_gen.pack(side=tk.RIGHT, padx=2)
        ToolTip(self.btn_multi_gen, "Generate 3 alternative takes to choose from")

        self.btn_generate = ttk.Button(self.bot_f, text="⚡ Gen", command=lambda: self.generate_callback(self), width=7, style="Flat.TButton")
        self.btn_generate.pack(side=tk.RIGHT, padx=2)
        # ─────────────────────────────────────────────────────────────────────

        self.chk_retry_var = tk.BooleanVar(value=True)
        self.update_engine_indicator()

    def _on_speaker_changed(self, event=None):
        self.update_engine_indicator(event)
        if self.is_collapsed:
            self._refresh_collapsed_bar()

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self._refresh_collapsed_bar()
            self.expanded_content.pack_forget()
            self.collapsed_bar.pack(fill=tk.X)
            self.config(pady=2)
        else:
            self.collapsed_bar.pack_forget()
            self.expanded_content.pack(fill=tk.X)
            self.config(pady=5)

    def _refresh_collapsed_bar(self):
        """Populate the thin collapsed bar with current data."""
        speaker = self.speaker_var.get()
        text = self.text_input.get("1.0", tk.END).strip()
        preview = (text[:50] + "…") if len(text) > 50 else (text if text else "(no text)")
        self.lbl_col_speaker.config(text=f"🎙 {speaker}")
        self.lbl_col_preview.config(text=preview)
        # Draw small status dot
        c = self.status_light_col
        c.delete("all")
        color = STATUS_COLORS.get(self.status, STATUS_COLORS["pending"])
        c.create_oval(1, 1, 15, 15, fill=color, outline="")
        syms = {"success": "✔", "review": "?", "failed": "!", "busy": "⏳", "pending": "•", "queued": "•"}
        fg = "black" if self.status == "review" else "white"
        c.create_text(8, 8, text=syms.get(self.status, "•"), fill=fg, font=("Arial", 7, "bold"))

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
        if self.is_collapsed:
            self._refresh_collapsed_bar()
        
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
        self._block_counter = 0  # resets on clear/load, increments per new block
        self.script_name_var = tk.StringVar(value="New Script")
        
        # --- TOP TOOLBAR ---
        toolbar = tk.Frame(self, bg="#dfe6e9", padx=10, pady=10)
        toolbar.pack(fill=tk.X)
        
        ttk.Button(toolbar, text="➕ Add Block", command=self.add_block).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="➕ Clone Block", command=self.add_clone_block).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑 Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(toolbar, text="⊟ Collapse All", command=self.collapse_all_blocks).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⊞ Expand All", command=self.expand_all_blocks).pack(side=tk.LEFT, padx=2)
        
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
        
        # Scoped mousewheel — only scroll when cursor is over the canvas
        def _bind_mousewheel(event):
            self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        def _unbind_mousewheel(event):
            self.canvas.unbind("<MouseWheel>")
        self.canvas.bind("<Enter>", _bind_mousewheel)
        self.canvas.bind("<Leave>", _unbind_mousewheel)
        self.scroll_frame.bind("<Enter>", _bind_mousewheel)
        self.scroll_frame.bind("<Leave>", _unbind_mousewheel)

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
        self.auto_switch_var = tk.BooleanVar(value=True)
        self.chk_auto_switch = tk.Checkbutton(action_bar, text="⚡ Auto-Switch Engines", variable=self.auto_switch_var,
                                              bg="#2c3e50", fg="white", font=("Segoe UI", 10),
                                              selectcolor="#2c3e50", activebackground="#2c3e50", activeforeground="white")
        self.chk_auto_switch.pack(side=tk.RIGHT, padx=15)

        self.auto_verify_var = tk.BooleanVar(value=False)
        self.chk_auto_verify = tk.Checkbutton(
            action_bar, text="🔍 Auto-Verify Batch",
            variable=self.auto_verify_var,
            bg="#2c3e50", fg="white", font=("Segoe UI", 10),
            selectcolor="#2c3e50", activebackground="#2c3e50", activeforeground="white"
        )
        self.chk_auto_verify.pack(side=tk.RIGHT, padx=15)

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

    def collapse_all_blocks(self):
        """Collapse every block to its thin bar."""
        for b in self.blocks:
            if not b.is_collapsed:
                b.toggle_collapse()

    def expand_all_blocks(self):
        """Expand every block to full view."""
        for b in self.blocks:
            if b.is_collapsed:
                b.toggle_collapse()

    def _on_mousewheel(self, event):
        if event.delta:
            # Windows: delta is ±120 per tick; macOS: delta is ±1
            units = int(-1 * (event.delta / 120)) if abs(event.delta) >= 120 else int(-1 * event.delta)
        else:
            units = 0
        self.canvas.yview_scroll(units, "units")

    def get_speakers(self):
        # Combines Built-in Presets + Saved Design Profiles
        # Clones are excluded as they require a different model structure
        # Add Design Profiles (Design Mode)
        designs = list(self.app.design_profiles.keys())
        
        return PRESETS + ["---"] + designs

    def get_builtin_speakers(self):
        """Returns only the built-in preset voice names (green strip in UI)."""
        return list(PRESETS)

    def get_custom_voices(self):
        """Returns voice names that are NOT built-in presets (blue strip = design profiles)."""
        return list(self.app.design_profiles.keys())

    def get_styles(self):
        return sorted(list(self.app.app_config.get("style_instructions", {}).keys()))

    def get_clone_profiles(self):
        return sorted(list(self.app.voice_configs.keys()))

    def add_clone_block(self):
        self.add_block("clone")

    def add_block(self, block_type="standard"):
        speakers = self.get_speakers()
        styles = self.get_styles()
        self._block_counter += 1
        block = ScriptBlock(self.scroll_frame, len(self.blocks), self.remove_block, self.generate_single_block, speakers, styles, self.app, block_type=block_type, block_number=self._block_counter)
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
            self._block_counter = 0
            self.add_block()

    def save_script(self):
        """Saves current blocks to JSON, and any generated audio to a companion folder."""
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Scripts", "*.json")])
        if not f: return

        # 1. Prepare companion audio directory
        base_dir = os.path.dirname(f)
        base_name = os.path.splitext(os.path.basename(f))[0]
        audio_dir_name = f"{base_name}_audio"
        audio_dir_path = os.path.join(base_dir, audio_dir_name)

        has_audio = False
        data = []

        for i, b in enumerate(self.blocks):
            block_data = {
                "type": b.block_type,
                "speaker": b.speaker_var.get(),
                "style": b.style_var.get(),
                "language": b.lang_var.get(),
                "text": b.text_input.get("1.0", tk.END).strip(),
                "temp": b.temp_var.get(),
                "top_p": b.top_p_var.get(),
                "seed": b.seed_var.get(),
                "status": b.status,
                "audio_file": None
            }

            # 2. Save audio if it exists and has been approved/reviewed
            if b.generated_audio is not None and b.status in ["success", "review"]:
                if not has_audio:
                    os.makedirs(audio_dir_path, exist_ok=True)
                    has_audio = True

                # Format: 001_SpeakerName.wav
                spk_clean = "".join(x for x in block_data["speaker"] if x.isalnum())
                audio_filename = f"{i+1:03d}_{spk_clean}.wav"
                full_audio_path = os.path.join(audio_dir_path, audio_filename)

                try:
                    sf.write(full_audio_path, b.generated_audio, b.sample_rate)
                    # Store RELATIVE path so the folder and JSON can be moved together
                    block_data["audio_file"] = os.path.join(audio_dir_name, audio_filename).replace("\\", "/")
                except Exception as e:
                    print(f"Failed to save audio for block {i+1}: {e}")

            data.append(block_data)

        try:
            with open(f, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2)
            self.script_name_var.set(os.path.basename(f))

            msg = f"Script saved to {os.path.basename(f)}"
            if has_audio:
                msg += f"\nAudio saved to companion folder: {audio_dir_name}/"
            messagebox.showinfo("Saved", msg)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_script(self):
        """Loads blocks from JSON and attempts to link their companion audio."""
        f = filedialog.askopenfilename(filetypes=[("JSON Scripts", "*.json")])
        if not f: return

        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)

            if not isinstance(data, list): raise Exception("Invalid format")

            # Pass the base directory so we can resolve relative audio paths
            base_dir = os.path.dirname(f)
            loaded_audio_count = self.load_script_data(data, name=os.path.basename(f), base_dir=base_dir)

            msg = f"Loaded {len(data)} blocks."
            if loaded_audio_count > 0:
                msg += f"\nSuccessfully restored {loaded_audio_count} audio renders."
            messagebox.showinfo("Loaded", msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load script:\n{e}")

    def load_script_data(self, data, name="Custom Script", base_dir=None):
        """Programmatically loads blocks from a list of dicts. Resolves audio if base_dir is provided."""
        if not isinstance(data, list): return 0

        # Clear existing
        for b in self.blocks: b.destroy()
        self.blocks = []
        self._block_counter = 0
        self.script_name_var.set(name)

        available_styles = self.get_styles()
        loaded_audio_count = 0

        for item in data:
            b = self.add_block(item.get("type", item.get("block_type", "standard")))
            b.speaker_var.set(item.get("speaker", ""))
            b.text_input.insert("1.0", item.get("text", ""))

            if "temp" in item: b.temp_var.set(item["temp"])
            if "top_p" in item: b.top_p_var.set(item["top_p"])
            if "seed" in item: b.seed_var.set(str(item["seed"]))
            if "language" in item: b.lang_var.set(item["language"])

            # Check Style availability
            st = item.get("style", "")
            if st and st not in available_styles:
                st = "---"
            b.style_var.set(st)

            # Guard against empty language strings saved by older versions
            if not b.lang_var.get():
                b.lang_var.set("English")

            # --- AUDIO RESTORATION LOGIC ---
            audio_file = item.get("audio_file")
            saved_status = item.get("status", "pending")

            # Only honour success/review status when audio was actually restored.
            # If the audio companion folder is missing, degrade to pending so
            # the block gets re-generated rather than silently crashing on Run.
            audio_restored = False

            if audio_file and base_dir:
                audio_path = os.path.join(base_dir, os.path.normpath(audio_file))
                if os.path.exists(audio_path):
                    try:
                        audio_data, sr = sf.read(audio_path)
                        b.generated_audio = audio_data
                        b.sample_rate = sr
                        audio_restored = True
                        loaded_audio_count += 1
                    except Exception as e:
                        print(f"Failed to load audio {audio_path}: {e}")
                else:
                    print(f"Audio file not found, marking pending: {audio_path}")

            if audio_restored:
                b.set_status(saved_status)
            elif saved_status in ("success", "review"):
                # Had audio before but file is gone — re-queue for generation
                b.set_status("pending")
            else:
                # Preserve failed/pending as-is; never restore busy/queued
                b.set_status(saved_status if saved_status not in ("busy", "queued") else "pending")

            # Update visual indicator
            b.update_engine_indicator(load_defaults=False)

        return loaded_audio_count

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

        # Pre-read all Tkinter widget values on the main thread (Tkinter is not thread-safe)
        block_data_map = {}
        for b in final_queue:
            block_data_map[id(b)] = {
                "text": b.text_input.get("1.0", tk.END).strip(),
                "speaker": b.speaker_var.get(),
                "lang": b.lang_var.get(),
                "style": b.style_var.get(),
                "temp": b.temp_var.get(),
                "top_p": b.top_p_var.get(),
                "seed": b.seed_var.get().strip(),
            }

        self.app.set_busy(True, "Directing Scene...")
        self.btn_run.config(state=tk.DISABLED)

        threading.Thread(target=self._generation_worker, args=(final_queue, block_data_map), daemon=True).start()

    def generate_single_block(self, block):
        """Generate audio for one specific block without touching others."""
        if not self.app.model:
            messagebox.showerror("Error", "Model not loaded!")
            return
        if self.btn_run['state'] == tk.DISABLED:
            messagebox.showwarning("Busy", "Generation already running. Please wait.")
            return

        # Pre-read widget values on main thread
        block_data_map = {
            id(block): {
                "text": block.text_input.get("1.0", tk.END).strip(),
                "speaker": block.speaker_var.get(),
                "lang": block.lang_var.get(),
                "style": block.style_var.get(),
                "temp": block.temp_var.get(),
                "top_p": block.top_p_var.get(),
                "seed": block.seed_var.get().strip(),
            }
        }

        self.app.set_busy(True, f"Generating block #{block.block_number}...")
        self.btn_run.config(state=tk.DISABLED)
        threading.Thread(
            target=self._generation_worker,
            args=([block], block_data_map),
            kwargs={"play_on_complete": False},
            daemon=True
        ).start()

    # ── Multi-Take ────────────────────────────────────────────────────────────

    def generate_multi_takes(self, block):
        """Generate 3 variations of one block and let the user pick the best."""
        if not self.app.model:
            messagebox.showerror("Error", "Model not loaded!")
            return
        if self.btn_run['state'] == tk.DISABLED:
            messagebox.showwarning("Busy", "Generation already running. Please wait.")
            return

        # Pre-read on main thread
        mt_data = {
            "text": block.text_input.get("1.0", tk.END).strip(),
            "speaker": block.speaker_var.get(),
            "lang": block.lang_var.get(),
            "style": block.style_var.get(),
            "temp": block.temp_var.get(),
            "top_p": block.top_p_var.get(),
        }

        self.app.set_busy(True, f"Generating 3 takes for block #{block.block_number}...")
        self.btn_run.config(state=tk.DISABLED)
        threading.Thread(target=self._multi_take_worker, args=(block, mt_data), daemon=True).start()

    def _multi_take_worker(self, block, mt_data):
        """Background thread: engine check → 3-take loop → open picker."""

        # --- Helpers called on the main thread via root.after ---
        def _fail(msg):
            self.app.set_busy(False)
            self.btn_run.config(state=tk.NORMAL)
            self.lbl_progress.config(text="Multi-take failed.")
            messagebox.showerror("Multi-Take Error", msg)

        def _cancel():
            self.app.set_busy(False)
            self.btn_run.config(state=tk.NORMAL)
            self.lbl_progress.config(text="Multi-take cancelled.")

        def _open(takes):
            self.app.set_busy(False)
            self.btn_run.config(state=tk.NORMAL)
            self.lbl_progress.config(text="Multi-take complete — pick your take.")
            self._show_take_picker(block, takes)

        # --- Use pre-read block fields (thread-safe) ---
        text = mt_data["text"]
        if not text:
            self.app.root.after(0, lambda: _fail("Block has no text."))
            return

        speaker_selection = mt_data["speaker"]
        lang = mt_data["lang"]
        if not lang or lang == "Auto":
            lang = "English"

        style_name = mt_data["style"]
        temp = mt_data["temp"]
        top_p = mt_data["top_p"]
        instruction = self.app.app_config.get("style_instructions", {}).get(style_name, "")

        # --- Step A: Determine required engine ---
        if block.block_type == "clone":
            required_mode = "base"
        elif speaker_selection in PRESETS:
            required_mode = "custom"
        else:
            required_mode = "design"

        if self.app.current_model_type != required_mode:
            should_switch = self.auto_switch_var.get()

            if not should_switch:
                user_response = [None]
                def ask_switch():
                    msg = (f"Multi-take needs the {required_mode.upper()} engine, "
                           f"but {self.app.current_model_type.upper()} is loaded.\n\n"
                           f"Switch engines now?")
                    user_response[0] = messagebox.askyesno("Switch Engine", msg)
                self.app.root.after(0, ask_switch)
                while user_response[0] is None:
                    if self.app.cancel_signal.is_set():
                        break
                    time.sleep(0.1)
                if user_response[0]:
                    should_switch = True

            if not should_switch or self.app.cancel_signal.is_set():
                self.app.root.after(0, _cancel)
                return

            switch_msg = f"Switching to {required_mode.upper()} engine..."
            self.app.root.after(0, lambda m=switch_msg: self.lbl_progress.config(text=m))
            try:
                self.app.switch_model(required_mode)
                timeout = 90
                if not self.app._model_load_event.wait(timeout=timeout):
                    raise Exception("Model load timed out.")
                if self.app.cancel_signal.is_set():
                    self.app.root.after(0, _cancel)
                    return
                if self.app.current_model_type != required_mode or self.app.model is None:
                    raise Exception("Model failed to load.")
                time.sleep(1)
            except Exception as e:
                err = str(e)
                self.app.root.after(0, lambda er=err: _fail(er))
                return

        # --- Meta-Tensor Safety Guard ---
        # Sample params from multiple depths: a partial VRAM load puts early layers on
        # CUDA and later layers on "meta", so checking only param[0] misses the failure.
        try:
            if self.app.model is None:
                raise RuntimeError("Model not loaded.")
            if hasattr(self.app.model, "model") and hasattr(self.app.model.model, "parameters"):
                checked = 0
                for p in self.app.model.model.parameters():
                    if str(p.device) == "meta":
                        _deep_destroy_model(self.app)
                        raise RuntimeError(
                            "VRAM Overflow: The engine entered a corrupted meta state. "
                            "Memory has been forcefully purged. Use the Reset button to reload.")
                    checked += 1
                    if checked >= 20:  # sample first 20 params across early and mid layers
                        break
        except RuntimeError as e:
            err = str(e)
            self.app.root.after(0, lambda er=err: messagebox.showerror("VRAM Error", er))
            self.app.root.after(0, lambda: self.app.set_busy(False))
            self.app.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL))
            return

        # --- Pre-resolve clone prompt and design profile (once, outside loop) ---
        cached_prompt = None
        design_desc = ""
        design_instruct = instruction

        if required_mode == "base":
            try:
                self.app.root.after(0, lambda: self.lbl_progress.config(
                    text=f"Locking voice: {speaker_selection}..."))
                profile_data = self.app.voice_configs.get(speaker_selection)
                if not profile_data:
                    raise Exception("Clone profile not found.")
                audio_path = profile_data.get("audio_path")
                ref_txt = profile_data.get("transcript")
                if not audio_path or not os.path.exists(audio_path):
                    raise Exception("Source audio file missing.")
                cached_prompt = self.app.model.create_voice_clone_prompt(
                    ref_audio=audio_path, ref_text=ref_txt)
            except Exception as e:
                err = str(e)
                self.app.root.after(0, lambda er=err: _fail(er))
                return

        elif required_mode == "design":
            profile = self.app.design_profiles.get(speaker_selection)
            if not profile and hasattr(self.app, 'voice_recipes'):
                profile = self.app.voice_recipes.get(speaker_selection)
            if not profile:
                self.app.root.after(0, lambda: _fail(f"Profile '{speaker_selection}' not found."))
                return
            design_desc = profile.get("desc", "")
            prof_instruct = profile.get("instruct", "")
            design_instruct = f"{instruction}. {prof_instruct}" if instruction else prof_instruct

        # --- Step B: Generation loop ---
        takes = []
        for i in range(3):
            if self.app.cancel_signal.is_set():
                break

            current_seed = random.randint(0, 0xFFFFFFFF)
            n = i + 1
            self.app.root.after(0, lambda n=n: self.lbl_progress.config(
                text=f"Generating take {n}/3..."))

            try:
                wavs = None
                sr = 24000

                if required_mode == "custom":
                    wavs, sr = self.app.model.generate_custom_voice(
                        text=text, speaker=speaker_selection,
                        instruct=instruction, language=lang,
                        temperature=temp, top_p=top_p, seed=current_seed)

                elif required_mode == "design":
                    wavs, sr = self.app.model.generate_voice_design(
                        text=text, voice_description=design_desc,
                        instruct=design_instruct, language=lang,
                        temperature=temp, top_p=top_p, seed=current_seed)

                elif required_mode == "base":
                    wavs, sr = self.app.model.generate_voice_clone(
                        text=text, language=lang,
                        voice_clone_prompt=cached_prompt,
                        temperature=temp, top_p=top_p, seed=current_seed)

                if wavs:
                    takes.append({"audio": wavs[0], "sr": sr, "seed": current_seed})

            except Exception as e:
                err_str = str(e).lower()
                if "meta tensor" in err_str or ("meta" in err_str and "tensor" in err_str):
                    # Broken model — deep-destroy and abort all remaining takes.
                    _deep_destroy_model(self.app)
                    self.app.root.after(0, lambda: _fail(
                        "VRAM Overflow: The engine entered a meta state during generation.\n\n"
                        "Memory has been purged. Use the \u21ba Reset button to reload the engine."))
                    return
                print(f"Multi-take {i + 1} failed: {e}")
            finally:
                self.app.flush_vram()

        # --- Step C: Completion ---
        if not takes:
            self.app.root.after(0, lambda: _fail("All 3 takes failed to generate."))
            return

        self.app.root.after(0, lambda t=takes: _open(t))

    def _show_take_picker(self, block, takes):
        """Modal dialog: play each take and accept the best one."""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Select Best Take")
        dialog.resizable(False, False)
        dialog.transient(self.app.root)
        dialog.grab_set()

        tk.Label(dialog,
                 text=f"Block #{block.block_number}  —  pick the best take",
                 font=("Segoe UI", 11, "bold"),
                 padx=20, pady=12).pack()

        ttk.Separator(dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        def on_close():
            sd.stop()
            self.app.set_busy(False)
            self.btn_run.config(state=tk.NORMAL)
            dialog.destroy()

        def accept(take):
            sd.stop()
            block.generated_audio = take["audio"]
            block.sample_rate = take["sr"]
            block.seed_var.set(str(take["seed"]))
            block.set_status("review")
            on_close()

        for i, take in enumerate(takes):
            row = tk.Frame(dialog, pady=8, padx=20)
            row.pack(fill=tk.X)
            tk.Label(row,
                     text=f"Take {i + 1}   (Seed: {take['seed']})",
                     font=("Segoe UI", 10), width=30, anchor="w").pack(side=tk.LEFT)
            ttk.Button(row, text="▶ Play", width=8,
                       command=lambda t=take: [sd.stop(), sd.play(t["audio"], t["sr"])]
                       ).pack(side=tk.LEFT, padx=(0, 6))
            ttk.Button(row, text="✔ Accept", width=8,
                       command=lambda t=take: accept(t)
                       ).pack(side=tk.LEFT)

        ttk.Separator(dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(8, 0))
        ttk.Button(dialog, text="Discard all takes",
                   command=on_close
                   ).pack(pady=10)

        dialog.protocol("WM_DELETE_WINDOW", on_close)

    # ── End Multi-Take ────────────────────────────────────────────────────────

    def retry_marked_blocks(self):
        # Deprecated: functionality moved to main run button
        self.start_scene_generation()

    def _generation_worker(self, queue, block_data_map=None, play_on_complete=True):
        total = len(queue)

        # Sanity-check: detect meta-tensor state before processing any blocks.
        # This happens when a model switch or fresh load did not fully materialise
        # weights onto a real device.  Fail fast with a clear message instead of
        # letting every block silently crash with "Tensor.item() cannot be called
        # on meta tensors".
        try:
            if self.app.model is None:
                raise RuntimeError("No model loaded. Please load a model before generating.")
            if hasattr(self.app.model, "model") and hasattr(self.app.model.model, "parameters"):
                checked = 0
                for p in self.app.model.model.parameters():
                    if str(p.device) == "meta":
                        _deep_destroy_model(self.app)
                        raise RuntimeError(
                            "VRAM Overflow: The engine entered a corrupted meta state. "
                            "Memory has been forcefully purged. Use the Reset button to reload.")
                    checked += 1
                    if checked >= 20:
                        break
        except RuntimeError as probe_err:
            err_msg = str(probe_err)
            self.app.root.after(0, lambda e=err_msg: messagebox.showerror("Model Error", e))
            self.app.root.after(0, self.app.set_busy, False)
            self.app.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL))
            self.app.root.after(0, lambda: self.lbl_progress.config(text="Generation failed - model not ready."))
            return

        # State for Clone Prompt Caching
        current_clone_speaker = None
        cached_prompt = None

        # Tracks engine mode when a meta-tensor abort breaks the loop (for auto-recovery)
        _meta_abort_mtype = None

        for i, block in enumerate(queue):
            if self.app.cancel_signal.is_set(): break
            
            bdata = block_data_map[id(block)] if block_data_map else {}
            text = bdata.get("text", block.text_input.get("1.0", tk.END).strip())
            speaker_selection = bdata.get("speaker", block.speaker_var.get())
            lang = bdata.get("lang", block.lang_var.get())

            # Guard: empty / "Auto" language can cause meta-tensor crashes in some
            # model builds. Fall back to "English" if blank.
            if not lang or lang == "Auto":
                lang = "English"

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
                    timeout = 90  # seconds
                    if not self.app._model_load_event.wait(timeout=timeout):
                        raise Exception("Model load timed out.")
                    if self.app.cancel_signal.is_set():
                        break
                    if self.app.current_model_type != required_mode or self.app.model is None:
                        raise Exception("Model failed to load.")

                    # 4. Stabilization Period
                    time.sleep(1)

                except Exception as e:
                    print(f"Failed to switch model: {e}")
                    self.app.root.after(0, lambda b=block: b.set_status("failed"))
                    break

            # Update UI from thread
            self.app.root.after(0, lambda b=block: b.set_status("busy"))
            self.app.root.after(0, lambda idx=i+1: self.lbl_progress.config(text=f"Generating block {idx}/{total}..."))
            
            style_name = bdata.get("style", block.style_var.get())
            temp = bdata.get("temp", block.temp_var.get())
            top_p = bdata.get("top_p", block.top_p_var.get())
            instruction = self.app.app_config.get("style_instructions", {}).get(style_name, "")

            # Resolve seed: use stored value or generate a fresh random one.
            # If random, write it back into the block's entry so it's saved with the script.
            try:
                raw_seed = bdata.get("seed", block.seed_var.get().strip())
                block_seed = int(raw_seed)
                if block_seed < 0:
                    raise ValueError
            except (ValueError, AttributeError):
                block_seed = random.randint(0, 0xFFFFFFFF)
                self.app.root.after(0, lambda s=block_seed, b=block: b.seed_var.set(str(s)))

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
                        temperature=temp, top_p=top_p, seed=block_seed
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
                        temperature=temp, top_p=top_p, seed=block_seed
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
                        temperature=temp, top_p=top_p, seed=block_seed
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

                    self.app.flush_vram()

                else:
                    raise Exception("No audio returned")

            except Exception as e:
                err_str = str(e).lower()
                if "meta tensor" in err_str or ("meta" in err_str and "tensor" in err_str):
                    _meta_abort_mtype = required_mode
                    _deep_destroy_model(self.app)
                    self.app.root.after(0, lambda b=block: b.set_status("failed"))
                    break
                print(f"Block failed: {e}")
                self.app.root.after(0, lambda b=block: b.set_status("failed"))
        
        def on_complete():
            self.app.set_busy(False)
            self.btn_run.config(state=tk.NORMAL)
            self.lbl_progress.config(text="Scene Complete")
            if play_on_complete and self.auto_switch_var.get():
                self.play_scene()

        if _meta_abort_mtype:
            # Auto-recover: reload the engine then re-enable UI and inform the user.
            # UI stays locked (btn_run disabled) until the reload is complete.
            def _do_recover():
                self.lbl_progress.config(text="VRAM overflow — reloading engine…")
                self.app.current_model_type = None  # force switch_model to actually reload
                def _on_recovered():
                    self.btn_run.config(state=tk.NORMAL)
                    self.lbl_progress.config(text="Engine reloaded. Review failed blocks and re-run.")
                    messagebox.showwarning(
                        "VRAM Overflow — Recovered",
                        "The engine hit a VRAM overflow mid-batch.\n\n"
                        "Remaining blocks were skipped. The engine has been reloaded automatically.\n"
                        "Review the failed blocks (red ✗) and click Run Scene to regenerate them.")
                self.app.switch_model(_meta_abort_mtype, on_success=_on_recovered)
            self.app.root.after(0, _do_recover)
        elif self.auto_verify_var.get():
            # on_complete is handed off to _auto_verify_pass, which calls it only after
            # the engine has been fully reloaded, keeping the UI locked until then.
            self._auto_verify_pass(queue, on_complete=on_complete)
        else:
            self.app.root.after(0, on_complete)

    def _auto_verify_pass(self, queue, on_complete=None):
        """
        Post-generation audit. Runs in the background thread.
        VRAM sequence: Qwen3 purge -> Whisper load -> audit loop -> Whisper purge -> engine reload.
        on_complete is called only after the engine is fully reloaded so the UI stays locked
        throughout the entire verify cycle.
        """
        saved_mtype = self.app.current_model_type

        def _reload_engine(label_text):
            """Schedule engine reload from main thread; call on_complete when ready."""
            self.app.current_model_type = None  # force switch_model to actually load
            def _after_reload():
                if on_complete:
                    on_complete()
                self.lbl_progress.config(text=label_text)
            self.app.root.after(0, lambda: self.app.switch_model(saved_mtype, on_success=_after_reload))

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            self.app.root.after(0, lambda: messagebox.showerror(
                "Whisper Not Found",
                "Auto-Verify requires faster-whisper.\n\n"
                "Run:  pip install faster-whisper\nthen restart the application."
            ))
            # Model was never touched — just unblock the UI.
            if on_complete:
                self.app.root.after(0, on_complete)
            return

        # --- 1. Purge Qwen3 from VRAM ---
        self.app.root.after(0, lambda: self.lbl_progress.config(text="Auto-Verify: Purging VRAM..."))
        _deep_destroy_model(self.app)   # deep teardown: HF model → processor → wrapper → flush
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        time.sleep(2)                   # let the CUDA driver reclaim pages before Whisper loads

        # --- 2. Load Whisper ---
        self.app.root.after(0, lambda: self.lbl_progress.config(text="Auto-Verify: Loading Whisper..."))
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        try:
            whisper_model = WhisperModel("small", device=device, compute_type=compute_type)
        except Exception as e:
            err = str(e)
            self.app.root.after(0, lambda: messagebox.showerror("Whisper Load Error", err))
            _reload_engine("Auto-Verify failed (Whisper load error).")
            return

        # --- 3. Audit loop ---
        total_audited = 0
        flagged = 0

        for block in queue:
            if block.generated_audio is None:
                continue
            total_audited += 1
            block_text = block.text_input.get("1.0", tk.END).strip()
            failure_reason = None

            # Check 1: silence detection (pure numpy, no I/O)
            passed, msg = detect_long_pauses(block.generated_audio, block.sample_rate)
            if not passed:
                failure_reason = msg

            # Check 2: transcription similarity (only if silence passed)
            if failure_reason is None:
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp_path = tmp.name
                    sf.write(tmp_path, block.generated_audio, block.sample_rate)
                    segs, _ = whisper_model.transcribe(tmp_path)
                    transcription = " ".join(s.text for s in segs).strip()
                    passed_t, msg_t = verify_transcription(block_text, transcription)
                    if not passed_t:
                        failure_reason = msg_t
                except Exception as e:
                    failure_reason = f"Transcription error: {e}"
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass

            if failure_reason:
                flagged += 1
                reason = failure_reason
                def _flag(b=block, r=reason):
                    b.set_status("review")
                    ToolTip(b.status_light, f"⚠ Auto-Verify: {r}")
                self.app.root.after(0, _flag)

        # --- 4. Unload Whisper ---
        del whisper_model
        self.app.flush_vram()

        # --- 5. Reload engine (unblocks UI when done) ---
        summary = f"Auto-Verify complete: {total_audited} audited, {flagged} flagged for review."
        _reload_engine(summary)

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
        """Concatenates audio blocks into one WAV.
        
        Render logic:
          - green (success) + yellow (review) → always included
          - red (failed) / grey (pending) / queued → skipped, but user is warned
          - If any review/unknown blocks exist → ask for confirmation first
        """
        # Categorise blocks
        include = []   # success or review WITH audio
        missing = []   # failed / pending / queued (no usable audio)
        review  = []   # review blocks (audio present but unconfirmed)

        for b in self.blocks:
            num = f"#{b.block_number}" if b.block_number else f"block"
            if b.status in ("success", "review") and b.generated_audio is not None:
                include.append(b)
                if b.status == "review":
                    review.append(num)
            else:
                missing.append((num, b.status))

        # Nothing at all to render
        if not include:
            messagebox.showwarning("Nothing to Render",
                "No generated audio found.\n\nRun the scene first, then render.")
            return

        # Warn about blocks that will be SKIPPED
        skip_msgs = []
        red_blocks   = [n for n, s in missing if s == "failed"]
        grey_blocks  = [n for n, s in missing if s in ("pending", "queued")]

        if red_blocks:
            skip_msgs.append(f"⛔  Rejected (red) — will be skipped:\n    {', '.join(red_blocks)}")
        if grey_blocks:
            skip_msgs.append(f"⚪  Not generated (grey) — will be skipped:\n    {', '.join(grey_blocks)}")

        # Warn about unconfirmed review blocks that WILL be included
        confirm_msgs = []
        if review:
            confirm_msgs.append(f"🟡  Unconfirmed (yellow) — will be included:\n    {', '.join(review)}")

        # Build the prompt
        if skip_msgs or confirm_msgs:
            lines = ["Some blocks need your attention before rendering:\n"]
            lines += confirm_msgs
            lines += skip_msgs
            lines += ["\nProceed with the render?"]
            if not messagebox.askyesno("Render Review", "\n".join(lines)):
                return

        # Build audio
        audio_segments = []
        valid_sr = 24000
        for b in include:
            audio_segments.append(b.generated_audio)
            valid_sr = b.sample_rate
            silence = np.zeros(int(valid_sr * 0.2))
            audio_segments.append(silence)

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

            n_included = len(include)
            n_skipped  = len(missing)
            detail = f"{n_included} block(s) rendered"
            if n_skipped:
                detail += f", {n_skipped} skipped"
            messagebox.showinfo("Export Complete", f"Scene rendered successfully.\n{detail}")

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