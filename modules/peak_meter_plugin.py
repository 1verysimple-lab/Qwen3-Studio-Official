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
        self.geometry("150x350")
        self.attributes("-toolwindow", True)
        self.resizable(False, False) # Let's make it fixed for a cleaner look

        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Use a modern, dark theme
        self.configure(bg="#2b2b2b")

        self.canvas = tk.Canvas(self, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)

        # Meter configuration
        self.num_segments = 40 # More segments for a smoother gradient
        self.padding = 15
        self.meter_width = 35
        
        # dB range
        self.min_db = -50
        self.max_db = 6 # Allow for clipping indication
        
        # Peak hold state
        self.peak_l = self.min_db
        self.peak_r = self.min_db
        self.last_peak_update = time.time()
        self.peak_hold_duration = 1.5 # seconds
        self.peak_falloff = 20 # dB per second

        # Pre-calculate gradient
        self.gradient_colors = self._create_gradient("#2ecc71", "#f1c40f", "#e74c3c", self.num_segments)

        self._audio_data = None
        self._sample_rate = None
        self._analyzer_thread = None
        self._stop_analyzer = threading.Event()
        
        # --- EFFICIENT DRAWING ---
        # Create persistent items instead of redrawing everything
        self.channel_items = {'L': {'segs': [], 'peak': None}, 'R': {'segs': [], 'peak': None}}
        self.draw_meter_statics() # Draw the scale and bkg once
        self._peak_fall_loop() # Start the loop for peak line decay
        
    def _create_gradient(self, start_hex, mid_hex, end_hex, steps):
        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_hex(r, g, b):
            return f'#{r:02x}{g:02x}{b:02x}'

        start_rgb = hex_to_rgb(start_hex)
        mid_rgb = hex_to_rgb(mid_hex)
        end_rgb = hex_to_rgb(end_hex)
        
        colors = []
        mid_step = int(steps * 0.75)

        for i in range(steps):
            if i < mid_step:
                # Interpolate between green and yellow
                ratio = i / mid_step
                r = int(start_rgb[0] * (1 - ratio) + mid_rgb[0] * ratio)
                g = int(start_rgb[1] * (1 - ratio) + mid_rgb[1] * ratio)
                b = int(start_rgb[2] * (1 - ratio) + mid_rgb[2] * ratio)
            else:
                # Interpolate between yellow and red
                ratio = (i - mid_step) / (steps - mid_step)
                r = int(mid_rgb[0] * (1 - ratio) + end_rgb[0] * ratio)
                g = int(mid_rgb[1] * (1 - ratio) + end_rgb[1] * ratio)
                b = int(mid_rgb[2] * (1 - ratio) + end_rgb[2] * ratio)
            colors.append(rgb_to_hex(r,g,b))
        return colors

    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()

    def draw_meter_statics(self, event=None):
        self.canvas.delete("all")
        width = 150 # Use fixed width
        height = 350 # Use fixed height

        x_l = self.padding
        x_r = width - self.meter_width - self.padding
        self._draw_channel_statics(x_l, height, "L")
        self._draw_channel_statics(x_r, height, "R")
        
    def _draw_channel_statics(self, x_offset, height, channel_label):
        y_start = height - self.padding
        y_end = self.padding
        total_height = y_start - y_end
        
        # Create segment rectangles (initially hidden/dark)
        for i in range(self.num_segments):
            y1 = y_start - (i / self.num_segments) * total_height
            y2 = y_start - ((i + 1) / self.num_segments) * total_height + 1 # Overlap slightly
            
            rect = self.canvas.create_rectangle(x_offset, y1, x_offset + self.meter_width, y2,
                                                fill="#383838", outline="")
            self.channel_items[channel_label]['segs'].append(rect)

        # dB labels (white, smaller font)
        for db in [-40, -30, -20, -10, -3, 0, 6]:
            if self.min_db <= db <= self.max_db:
                y = y_start - ((db - self.min_db) / (self.max_db - self.min_db)) * total_height
                self.canvas.create_line(x_offset - 4, y, x_offset, y, fill="#aaa")
                self.canvas.create_text(x_offset - 7, y, text=str(db), fill="#aaa", anchor="e", font=("Segoe UI", 7))
        
        # Channel label
        self.canvas.create_text(x_offset + self.meter_width / 2, height - self.padding / 2 -2, text=channel_label, fill="#aaa", font=("Segoe UI", 9, "bold"))

        # Peak line (initially at bottom)
        peak_line = self.canvas.create_line(x_offset, y_start, x_offset + self.meter_width, y_start, fill="#f55")
        self.channel_items[channel_label]['peak'] = peak_line

    def analyze_audio(self, audio_data, sample_rate):
        if self._analyzer_thread and self._analyzer_thread.is_alive():
            self._stop_analyzer.set()
            self._analyzer_thread.join()

        self._audio_data = audio_data
        self._sample_rate = sample_rate
        self._stop_analyzer.clear()
        
        # Reset peaks on new audio
        self.peak_l = self.min_db
        self.peak_r = self.min_db

        self._analyzer_thread = threading.Thread(target=self._analyzer_loop, daemon=True)
        self._analyzer_thread.start()

    def _analyzer_loop(self):
        chunk_size = int(self._sample_rate / 25) # 25fps for smoother animation
        
        if len(self._audio_data.shape) == 1:
            audio_stereo = np.column_stack([self._audio_data, self._audio_data])
        else:
            audio_stereo = self._audio_data[:, :2] # Ensure max 2 channels

        num_chunks = len(audio_stereo) // chunk_size

        for i in range(num_chunks):
            if self._stop_analyzer.is_set():
                break

            start = i * chunk_size
            end = start + chunk_size
            chunk = audio_stereo[start:end]

            peak_l = np.max(np.abs(chunk[:, 0])) if chunk.size > 0 else 0
            peak_r = np.max(np.abs(chunk[:, 1])) if chunk.size > 0 else 0
            
            # Use a small epsilon to avoid log(0)
            db_l = 20 * np.log10(peak_l + 1e-9)
            db_r = 20 * np.log10(peak_r + 1e-9)
            
            self.update_levels(db_l, db_r)
            time.sleep(1/25.0)

        self.update_levels(self.min_db, self.min_db)

    def _peak_fall_loop(self):
        fall_amount = self.peak_falloff * 0.05 # dB fall per 50ms loop
        
        if time.time() - self.last_peak_update > self.peak_hold_duration:
            if self.peak_l > self.min_db:
                self.peak_l = max(self.min_db, self.peak_l - fall_amount)
            if self.peak_r > self.min_db:
                self.peak_r = max(self.min_db, self.peak_r - fall_amount)
        
        # Update peak line positions
        self._update_peak_line('L', self.peak_l)
        self._update_peak_line('R', self.peak_r)

        self.after(50, self._peak_fall_loop)

    def update_levels(self, db_l, db_r):
        self.after(0, self._update_canvas_levels, db_l, db_r)

    def _update_canvas_levels(self, db_l, db_r):
        if not self.winfo_exists(): return
        
        # Update peak values
        if db_l > self.peak_l:
            self.peak_l = db_l
            self.last_peak_update = time.time()
        if db_r > self.peak_r:
            self.peak_r = db_r
            self.last_peak_update = time.time()

        self._draw_level_indicator('L', db_l)
        self._draw_level_indicator('R', db_r)

    def _draw_level_indicator(self, channel, db_val):
        db_val = max(self.min_db, min(db_val, self.max_db))
        level_ratio = (db_val - self.min_db) / (self.max_db - self.min_db)
        active_segments = int(level_ratio * self.num_segments)

        for i, seg_rect in enumerate(self.channel_items[channel]['segs']):
            if i < active_segments:
                self.canvas.itemconfig(seg_rect, fill=self.gradient_colors[i])
            else:
                self.canvas.itemconfig(seg_rect, fill="#383838")
    
    def _update_peak_line(self, channel, db_val):
        if not self.winfo_exists(): return
        
        height = 350
        y_start = height - self.padding
        y_end = self.padding
        total_height = y_start - y_end
        
        db_val = max(self.min_db, min(db_val, self.max_db))
        level_height_ratio = (db_val - self.min_db) / (self.max_db - self.min_db)
        y = y_start - (level_height_ratio * total_height)
        
        line = self.channel_items[channel]['peak']
        x1, _, x2, _ = self.canvas.coords(line)
        self.canvas.coords(line, x1, y, x2, y)

def initialize(app):
    peak_meter_window = PeakMeter(app.root, app)
    peak_meter_window.withdraw()

    # Add a button to the UI to show the meter
    def toggle_peak_meter():
        if peak_meter_window.winfo_viewable():
            peak_meter_window.hide_window()
        else:
            peak_meter_window.show_window()
            try:
                # Position to the right of main window
                app.root.update_idletasks()
                x = app.root.winfo_x() + app.root.winfo_width() + 10
                y = app.root.winfo_y()
                peak_meter_window.geometry(f"+{x}+{y}")
            except: pass


    # Add button to the dedicated container in the main app
    btn_peak = tk.Button(
        app.vu_button_container, text="📶 VU", 
        command=toggle_peak_meter,
        bg=app.colors["accent"], fg="white",
        font=("Segoe UI", 8, "bold"), # Slightly smaller to fit
        activebackground=app.colors["accent_hover"],
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

