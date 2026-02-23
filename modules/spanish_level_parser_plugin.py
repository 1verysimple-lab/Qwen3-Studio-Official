import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os

def initialize(app):
    """
    Spanish Level JSON Parser Plugin
    - Loads a specific JSON format for a Spanish learning app.
    - Extracts text snippets (in Spanish and English).
    - Sends them to the Batch Studio for audio generation.
    """
    plugin_tab = ttk.Frame(app.notebook)
    app.notebook.add(plugin_tab, text="🇪🇸 Spanish Level Parser")

    # ── ROOT GRID ──────────────────────────────────────────────────────────
    plugin_tab.rowconfigure(0, weight=0)
    plugin_tab.rowconfigure(1, weight=1)
    plugin_tab.columnconfigure(0, weight=1)

    # ════════════════════════════════════════════════════════════════════════
    # UI FRAME
    # ════════════════════════════════════════════════════════════════════════
    ui_frame = ttk.Frame(plugin_tab, padding=(12, 8))
    ui_frame.grid(row=0, column=0, sticky="nsew")
    ui_frame.columnconfigure(1, weight=1)

    tk.Label(ui_frame, text="🇪🇸 Spanish Level Parser",
             font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
    tk.Label(ui_frame,
             text="Load a level JSON file to prepare for batch audio generation.",
             font=("Segoe UI", 9), fg="#555").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

    # ── Speaker Selection ──────────────────────────────────────────────────
    speaker_frame = ttk.LabelFrame(ui_frame, text=" Voice Assignment ", padding=(10, 6))
    speaker_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
    speaker_frame.columnconfigure(1, weight=1)

    # English Speaker
    ttk.Label(speaker_frame, text="English Voice:").grid(row=0, column=0, sticky="w", padx=(0, 5))
    speaker_en_var = tk.StringVar()
    speaker_en_combo = ttk.Combobox(speaker_frame, textvariable=speaker_en_var, state="readonly", width=25)
    speaker_en_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

    # Spanish Speaker
    ttk.Label(speaker_frame, text="Spanish Voice:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5,0))
    speaker_es_var = tk.StringVar()
    speaker_es_combo = ttk.Combobox(speaker_frame, textvariable=speaker_es_var, state="readonly", width=25)
    speaker_es_combo.grid(row=1, column=1, sticky="ew", pady=(5,0))

    # ── Generation Settings ────────────────────────────────────────────────
    settings_frame = ttk.LabelFrame(ui_frame, text=" Generation Settings ", padding=(10, 6))
    settings_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
    settings_frame.columnconfigure(1, weight=1)

    # Style
    ttk.Label(settings_frame, text="Style:").grid(row=0, column=0, sticky="w", padx=(0, 5))
    style_var = tk.StringVar()
    style_combo = ttk.Combobox(settings_frame, textvariable=style_var, state="readonly", width=25)
    style_combo.grid(row=0, column=1, sticky="ew")

    # Seed
    ttk.Label(settings_frame, text="Seed:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5,0))
    seed_var = tk.StringVar()
    seed_entry = ttk.Entry(settings_frame, textvariable=seed_var, width=27)
    seed_entry.grid(row=1, column=1, sticky="w", pady=(5,0))

    def refresh_dropdowns():
        """Populates speaker and style dropdowns from the director."""
        try:
            # Speakers
            speakers = app.director.get_speakers()
            speakers = [s for s in speakers if s != "---"]
            speaker_en_combo['values'] = speakers
            speaker_es_combo['values'] = speakers
            if speakers:
                if not speaker_en_var.get(): speaker_en_combo.current(0)
                if not speaker_es_var.get(): speaker_es_combo.current(0)

            # Styles
            styles = app.director.get_styles()
            style_combo['values'] = styles
            if styles and not style_var.get():
                style_combo.current(0)

        except Exception as e:
            print(f"Spanish Parser: Could not refresh dropdowns: {e}")

    # Defer dropdown loading to prevent race condition during startup
    app.root.after(200, refresh_dropdowns)
    
    # Refresh button
    ttk.Button(speaker_frame, text="↻", command=refresh_dropdowns, width=3).grid(row=0, column=2, rowspan=2)
    
    # ── File Loading ───────────────────────────────────────────────────────
    file_frame = ttk.Frame(ui_frame)
    file_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
    file_frame.columnconfigure(1, weight=1)

    ttk.Button(file_frame, text="📂 Load Level JSON...", command=lambda: load_json_file()).pack(side=tk.LEFT)
    
    loaded_file_var = tk.StringVar(value="No file loaded.")
    ttk.Label(file_frame, textvariable=loaded_file_var, font=("Segoe UI", 9, "italic"), foreground="#666").pack(side=tk.LEFT, padx=10)

    # ════════════════════════════════════════════════════════════════════════
    # LOGIC
    # ════════════════════════════════════════════════════════════════════════
    
    def is_spanish(text):
        """Rudimentary check for Spanish content."""
        text = text.lower()
        spanish_chars = ['¿', '¡', 'ñ']
        spanish_words = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'ser', 'se', 'no', 'por']
        
        if any(char in text for char in spanish_chars):
            return True
        
        word_count = 0
        for word in spanish_words:
            if f" {word} " in f" {text} ":
                word_count += 1
        
        # If more than a couple of common Spanish words appear, assume Spanish.
        return word_count > 2

    def parse_level_json(data, filename):
        """Parses the JSON data and prepares it for the batch director."""
        if 'audio_bank' not in data:
            messagebox.showerror("Invalid Format", "The JSON file does not contain an 'audio_bank' key.")
            return

        script_data = []
        speaker_en = speaker_en_var.get()
        speaker_es = speaker_es_var.get()
        style = style_var.get()
        seed = seed_var.get().strip()

        if not speaker_en or not speaker_es:
            messagebox.showwarning("No Speaker", "Please select both an English and a Spanish voice.")
            return

        for key, value in data['audio_bank'].items():
            text = value.get('text', '').strip()
            if not text:
                continue

            lang = "Spanish" if is_spanish(text) else "English"
            speaker = speaker_es if lang == "Spanish" else speaker_en

            entry = {
                "type": "standard",
                "speaker": speaker,
                "text": text,
                "language": lang,
                "style": style,
                "temp": 0.8,
                "top_p": 0.8,
                "seed": seed
            }
            script_data.append(entry)

        if not script_data:
            messagebox.showinfo("Empty", "No text found in the 'audio_bank' of the JSON file.")
            return

        # Confirm before sending
        if messagebox.askyesno("Confirm", f"Load {len(script_data)} audio blocks into Batch Studio?\nThis will replace the current scene."):
            try:
                app.director.load_script_data(script_data, name=os.path.basename(filename))
                app.notebook.select(app.tab_batch) # Switch to Batch Studio tab
                messagebox.showinfo("Success", f"{len(script_data)} blocks sent to Batch Studio.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send to Batch Studio:\n{e}")

    def load_json_file():
        """Opens a file dialog and triggers the parsing process."""
        filepath = filedialog.askopenfilename(
            title="Select a Spanish Level JSON file",
            filetypes=[("JSON files", "*.json")]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            loaded_file_var.set(os.path.basename(filepath))
            parse_level_json(data, filepath)
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON file. Could not parse.")
            loaded_file_var.set("Failed to load.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            loaded_file_var.set("Failed to load.")

    # Make the app object aware of the tab
    app.tab_spanish_parser = plugin_tab
