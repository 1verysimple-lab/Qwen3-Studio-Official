import tkinter as tk
from tkinter import ttk
import numpy as np
import threading
import time

class PeakMeter(tk.Toplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        
        self.title("Peak Meter")
        self.geometry("200x400")
        self.attributes("-toolwindow", True)
        self.resizable(True, True)

        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.colors = self.app.colors
        self.configure(bg=self.colors["header_bg"])

        self.canvas = tk.Canvas(self, bg="#1c1c1c", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Meter configuration
        self.num_segments = 20
        self.padding = 10
        self.meter_width = 30
        
        # dB range
        self.min_db = -60
        self.max_db = 0
        
        self._audio_data = None
        self._sample_rate = None
        self._analyzer_thread = None
        self._stop_analyzer = threading.Event()
        
        self.bind("<Configure>", self.draw_meter)
        self.draw_meter()

    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()

    def draw_meter(self, event=None):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        # Draw stereo channels
        self._draw_channel(self.padding, height, "L")
        self._draw_channel(width / 2 + self.padding / 2, height, "R")
        
    def _draw_channel(self, x_offset, height, channel_label):
        # Background
        self.canvas.create_rectangle(x_offset, self.padding, x_offset + self.meter_width, height - self.padding,
                                     fill="#333", outline="#555")

        # Segments
        y_start = height - self.padding
        y_end = self.padding
        total_height = y_start - y_end
        
        for i in range(self.num_segments):
            y1 = y_start - (i / self.num_segments) * total_height
            y2 = y_start - ((i + 1) / self.num_segments) * total_height
            
            color = self._get_segment_color(i)
            self.canvas.create_rectangle(x_offset, y1, x_offset + self.meter_width, y2,
                                         fill=color, outline="")

        # dB labels
        for db in [-60, -40, -20, -10, -6, 0]:
            y = y_start - ((db - self.min_db) / (self.max_db - self.min_db)) * total_height
            self.canvas.create_line(x_offset - 5, y, x_offset, y, fill="white")
            self.canvas.create_text(x_offset - 10, y, text=str(db), fill="white", anchor="e", font=("Segoe UI", 7))
        
        # Channel label
        self.canvas.create_text(x_offset + self.meter_width / 2, height - self.padding / 2, text=channel_label, fill="white", font=("Segoe UI", 9, "bold"))


    def _get_segment_color(self, index):
        if index > self.num_segments - 3:
            return "#e74c3c" # Red (Peak)
        elif index > self.num_segments - 6:
            return "#f1c40f" # Yellow (Warning)
        else:
            return "#2ecc71" # Green (Safe)

    def analyze_audio(self, audio_data, sample_rate):
        if self._analyzer_thread and self._analyzer_thread.is_alive():
            self._stop_analyzer.set()
            self._analyzer_thread.join()

        self._audio_data = audio_data
        self._sample_rate = sample_rate
        self._stop_analyzer.clear()
        
        self._analyzer_thread = threading.Thread(target=self._analyzer_loop, daemon=True)
        self._analyzer_thread.start()

    def _analyzer_loop(self):
        chunk_size = int(self._sample_rate / 20) # 20 updates per second
        
        # Ensure stereo
        if len(self._audio_data.shape) == 1:
            audio_stereo = np.column_stack([self._audio_data, self._audio_data])
        else:
            audio_stereo = self._audio_data

        num_chunks = len(audio_stereo) // chunk_size

        for i in range(num_chunks):
            if self._stop_analyzer.is_set():
                break

            start = i * chunk_size
            end = start + chunk_size
            chunk = audio_stereo[start:end]

            peak_l = np.max(np.abs(chunk[:, 0]))
            peak_r = np.max(np.abs(chunk[:, 1]))
            
            db_l = 20 * np.log10(peak_l) if peak_l > 0 else self.min_db
            db_r = 20 * np.log10(peak_r) if peak_r > 0 else self.min_db
            
            self.update_levels(db_l, db_r)
            
            time.sleep(1/20.0) # Match update rate

        # Reset levels after playback
        self.update_levels(self.min_db, self.min_db)


    def update_levels(self, db_l, db_r):
        self.after(0, self._update_canvas_levels, db_l, db_r)

    def _update_canvas_levels(self, db_l, db_r):
        self.draw_meter() # Redraw background and scale
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        self._draw_level_indicator(self.padding, height, db_l)
        self._draw_level_indicator(width / 2 + self.padding / 2, height, db_r)

    def _draw_level_indicator(self, x_offset, height, db_val):
        y_start = height - self.padding
        y_end = self.padding
        total_height = y_start - y_end

        # Clamp db_val
        db_val = max(self.min_db, min(db_val, self.max_db))
        
        level_height_ratio = (db_val - self.min_db) / (self.max_db - self.min_db)
        
        y_level = y_start - (level_height_ratio * total_height)
        
        self.canvas.create_rectangle(x_offset, y_start, x_offset + self.meter_width, y_level,
                                     fill="#444", outline="")
                                     
def initialize(app):
    peak_meter_window = PeakMeter(app.root, app)
    peak_meter_window.withdraw()

    # Add a button to the UI to show the meter
    def toggle_peak_meter():
        if peak_meter_window.winfo_viewable():
            peak_meter_window.hide_window()
        else:
            peak_meter_window.show_window()

    # Add button to the dedicated container in the main app
    btn_peak = tk.Button(
        app.vu_button_container, text="📶 VU", 
        command=toggle_peak_meter,
        bg=app.colors["warning"], fg="white",
        font=("Segoe UI", 8, "bold"), # Slightly smaller to fit
        activebackground=app.colors["danger"],
        relief="raised", bd=2
    )
    btn_peak.pack(fill=tk.BOTH, expand=True)

    # --- Monkey-patch the playback functions ---
    original_play_click = app.on_play_click
    
    def patched_play_click():
        if app.generated_audio is not None:
            peak_meter_window.analyze_audio(app.generated_audio, app.sample_rate)
        original_play_click()
    
    app.on_play_click = patched_play_click

    original_helper_play = app.helper_toggle_play
    
    def patched_helper_play():
        if app.helper_audio_data is not None and not app.helper_is_playing:
             peak_meter_window.analyze_audio(app.helper_audio_data, app.helper_samplerate)
        original_helper_play()

    app.helper_toggle_play = patched_helper_play
    
    # Patch history playback too
    original_hist_play = app.on_history_play
    def patched_hist_play():
        if not app.selected_history_files: return
        filename = list(app.selected_history_files)[0]
        path = os.path.join(app.temp_dir, filename)
        if os.path.exists(path):
            data, sr = app.load_audio_file(path)
            if data is not None:
                peak_meter_window.analyze_audio(data, sr)
        original_hist_play()
        
    app.on_history_play = patched_hist_play
    
    print("Peak Meter Plugin Initialized.")

