import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import re
import os

# Colour palette for the 3 character slots in the preview
CHAR_COLORS = ["#d6eaf8", "#d5f5e3", "#fdebd0"]   # blue / green / orange
CHAR_TEXT   = ["#1a5276", "#145a32", "#784212"]

LANGUAGES = [
    "Auto", "English", "Spanish", "French", "German", "Italian",
    "Portuguese", "Dutch", "Polish", "Russian", "Japanese", "Korean",
    "Chinese", "Arabic", "Hindi", "Turkish", "Swedish", "Norwegian",
    "Danish", "Finnish", "Czech", "Romanian", "Hungarian",
]

def initialize(app):
    """
    Text Parser Plugin — Screenplay-aware batch block generator.

    Workflow:
      1. Load or paste text (plain prose OR screenplay format)
      2. Assign up to 3 voices to detected characters (screenplay)
         OR choose a single voice (prose mode)
      3. Click  ▶ Prepare Script  — see a colour-coded live preview
      4. Optionally save detected cues as new styles
      5. Click  ✔ Send to Batch Studio
    """

    plugin_tab = ttk.Frame(app.notebook)
    app.notebook.add(plugin_tab, text="📄 Text Parser")

    # ── ROOT GRID — 3 rows: options | text input | bottom-bar ──────────────
    plugin_tab.rowconfigure(0, weight=0)   # options panel  (fixed)
    plugin_tab.rowconfigure(1, weight=1)   # text input     (grows)
    plugin_tab.rowconfigure(2, weight=0)   # bottom bar     (fixed)
    plugin_tab.columnconfigure(0, weight=1)

    # ════════════════════════════════════════════════════════════════════════
    # ROW 0 — OPTIONS PANEL
    # ════════════════════════════════════════════════════════════════════════
    top_panel = ttk.Frame(plugin_tab, padding=(12, 8))
    top_panel.grid(row=0, column=0, sticky="ew")
    top_panel.columnconfigure(1, weight=1)

    # ── Title ────────────────────────────────────────────────────────────────
    tk.Label(top_panel, text="📄 Text Parser",
             font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=6, sticky="w")
    tk.Label(top_panel,
             text="Load a screenplay or prose document, preview how it splits, then send to Batch Studio.",
             font=("Segoe UI", 9), fg="#555").grid(row=1, column=0, columnspan=6, sticky="w", pady=(0, 8))

    # ── Mode selector ────────────────────────────────────────────────────────
    ttk.Label(top_panel, text="Mode:").grid(row=2, column=0, sticky="w")
    mode_var = tk.StringVar(value="screenplay")
    mode_frame = ttk.Frame(top_panel)
    mode_frame.grid(row=2, column=1, sticky="w", padx=(4, 20))
    ttk.Radiobutton(mode_frame, text="Screenplay  (CHARACTER: cue text)",
                    variable=mode_var, value="screenplay").pack(side=tk.LEFT)
    ttk.Radiobutton(mode_frame, text="Prose  (plain paragraphs)",
                    variable=mode_var, value="prose").pack(side=tk.LEFT, padx=(12, 0))

    # ── Block type ───────────────────────────────────────────────────────────
    ttk.Label(top_panel, text="Block Type:").grid(row=2, column=2, sticky="w")
    block_type_var = tk.StringVar(value="standard")
    type_combo = ttk.Combobox(top_panel, textvariable=block_type_var,
                               values=["standard", "clone"], state="readonly", width=9)
    type_combo.grid(row=2, column=3, sticky="w", padx=(4, 20))

    # ── Max words ────────────────────────────────────────────────────────────
    ttk.Label(top_panel, text="Max words/block:").grid(row=2, column=4, sticky="w")
    max_words_var = tk.IntVar(value=30)
    ttk.Spinbox(top_panel, from_=5, to=100, textvariable=max_words_var,
                width=5).grid(row=2, column=5, sticky="w", padx=4)

    # ── Separator ────────────────────────────────────────────────────────────
    ttk.Separator(top_panel, orient="horizontal").grid(
        row=3, column=0, columnspan=6, sticky="ew", pady=6)

    # ── CAST FRAME — up to 3 voices ─────────────────────────────────────────
    cast_frame = ttk.LabelFrame(top_panel, text=" Cast — Voice Assignment ", padding=(10, 6))
    cast_frame.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(0, 4))
    cast_frame.columnconfigure((1, 3, 5), weight=1)

    # We'll store 3 slot dicts: {char_var, voice_var, style_var, row_widgets}
    slots = []
    SLOT_LABELS = ["Character 1", "Character 2", "Character 3"]

    for i in range(3):
        col_base = i * 2
        bg = CHAR_COLORS[i]

        badge = tk.Label(cast_frame, text=f"  {i+1}  ",
                         bg=bg, fg=CHAR_TEXT[i],
                         font=("Segoe UI", 8, "bold"), relief="flat")
        badge.grid(row=0, column=col_base, sticky="w", padx=(0 if i == 0 else 10, 4))

        char_var  = tk.StringVar(value=SLOT_LABELS[i])
        voice_var = tk.StringVar()
        style_var = tk.StringVar()
        lang_var  = tk.StringVar(value="Auto")

        char_entry = ttk.Entry(cast_frame, textvariable=char_var, width=13)
        char_entry.grid(row=0, column=col_base, sticky="w",
                        padx=(0 if i == 0 else 10, 0))

        # voice dropdown
        voice_label = ttk.Label(cast_frame, text="Voice:")
        voice_label.grid(row=1, column=col_base, sticky="w",
                         padx=(0 if i == 0 else 10, 0))
        voice_combo_i = ttk.Combobox(cast_frame, textvariable=voice_var,
                                      state="readonly", width=18)
        voice_combo_i.grid(row=1, column=col_base + 1 if i < 2 else col_base,
                            sticky="w", padx=4)

        # style dropdown
        style_label = ttk.Label(cast_frame, text="Style:")
        style_label.grid(row=2, column=col_base, sticky="w",
                         padx=(0 if i == 0 else 10, 0))
        style_combo_i = ttk.Combobox(cast_frame, textvariable=style_var,
                                      state="readonly", width=18)
        style_combo_i.grid(row=2, column=col_base + 1 if i < 2 else col_base,
                            sticky="w", padx=4)

        # language dropdown
        lang_label = ttk.Label(cast_frame, text="Lang:")
        lang_label.grid(row=3, column=col_base, sticky="w",
                        padx=(0 if i == 0 else 10, 0))
        lang_combo_i = ttk.Combobox(cast_frame, textvariable=lang_var,
                                     values=LANGUAGES, state="readonly", width=18)
        lang_combo_i.grid(row=3, column=col_base + 1 if i < 2 else col_base,
                           sticky="w", padx=4)

        slots.append({
            "char_var":   char_var,
            "voice_var":  voice_var,
            "style_var":  style_var,
            "lang_var":   lang_var,
            "voice_combo": voice_combo_i,
            "style_combo": style_combo_i,
            "lang_combo":  lang_combo_i,
        })

    # Prose-mode: single voice row (shown/hidden based on mode)
    prose_frame = ttk.Frame(top_panel)
    prose_frame.grid(row=5, column=0, columnspan=6, sticky="ew", pady=(2, 0))
    ttk.Label(prose_frame, text="Voice:").pack(side=tk.LEFT)
    prose_voice_var = tk.StringVar()
    prose_voice_combo = ttk.Combobox(prose_frame, textvariable=prose_voice_var,
                                      state="readonly", width=22)
    prose_voice_combo.pack(side=tk.LEFT, padx=(6, 20))
    ttk.Label(prose_frame, text="Style:").pack(side=tk.LEFT)
    prose_style_var = tk.StringVar()
    prose_style_combo = ttk.Combobox(prose_frame, textvariable=prose_style_var,
                                      state="readonly", width=22)
    prose_style_combo.pack(side=tk.LEFT, padx=6)
    ttk.Label(prose_frame, text="Lang:").pack(side=tk.LEFT, padx=(12, 0))
    prose_lang_var = tk.StringVar(value="Auto")
    prose_lang_combo = ttk.Combobox(prose_frame, textvariable=prose_lang_var,
                                     values=LANGUAGES, state="readonly", width=14)
    prose_lang_combo.pack(side=tk.LEFT, padx=6)

    # Precision
    prec_frame = ttk.Frame(top_panel)
    prec_frame.grid(row=6, column=0, columnspan=6, sticky="w", pady=(6, 0))
    ttk.Label(prec_frame, text="Temperature:").pack(side=tk.LEFT)
    temp_var = tk.DoubleVar(value=0.8)
    ttk.Spinbox(prec_frame, from_=0.1, to=1.5, increment=0.1,
                textvariable=temp_var, width=5).pack(side=tk.LEFT, padx=(4, 16))
    ttk.Label(prec_frame, text="Top P:").pack(side=tk.LEFT)
    top_p_var = tk.DoubleVar(value=0.8)
    ttk.Spinbox(prec_frame, from_=0.1, to=1.0, increment=0.1,
                textvariable=top_p_var, width=5).pack(side=tk.LEFT, padx=4)

    # ── Row 7: Cleaning + Cues side by side ────────────────────────────────
    bottom_options_row = ttk.Frame(top_panel)
    bottom_options_row.grid(row=7, column=0, columnspan=6, sticky="ew", pady=(6, 2))
    bottom_options_row.columnconfigure(1, weight=1)

    # LEFT: Cleaning options
    clean_frame = ttk.LabelFrame(bottom_options_row, text=" Cleaning ", padding=(8, 4))
    clean_frame.grid(row=0, column=0, sticky="nw", padx=(0, 8))

    sq_row = ttk.Frame(clean_frame)
    sq_row.pack(anchor="w")
    remove_sq_var = tk.BooleanVar(value=True)
    sq_mode_var   = tk.StringVar(value="all")
    ttk.Checkbutton(sq_row, text="[ ] brackets:", variable=remove_sq_var).pack(side=tk.LEFT)
    ttk.Radiobutton(sq_row, text="remove all",    variable=sq_mode_var, value="all").pack(side=tk.LEFT, padx=(8,2))
    ttk.Radiobutton(sq_row, text="keep content",  variable=sq_mode_var, value="keep").pack(side=tk.LEFT)

    par_row = ttk.Frame(clean_frame)
    par_row.pack(anchor="w", pady=(4, 0))
    remove_par_var = tk.BooleanVar(value=False)
    par_mode_var   = tk.StringVar(value="all")
    ttk.Checkbutton(par_row, text="( ) parens:",  variable=remove_par_var).pack(side=tk.LEFT)
    ttk.Radiobutton(par_row, text="remove all",   variable=par_mode_var, value="all").pack(side=tk.LEFT, padx=(8,2))
    ttk.Radiobutton(par_row, text="keep content", variable=par_mode_var, value="keep").pack(side=tk.LEFT)

    sym_row = ttk.Frame(clean_frame)
    sym_row.pack(anchor="w", pady=(4, 0))
    clean_sym_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(sym_row, text="Clean special symbols", variable=clean_sym_var).pack(side=tk.LEFT)

    # RIGHT: Cue → Style panel (always shown, populated after prepare)
    cue_frame = ttk.LabelFrame(bottom_options_row, text=" 💡 Detected Cues — Save as Styles ", padding=(8, 4))
    cue_frame.grid(row=0, column=1, sticky="nsew")
    cue_frame.columnconfigure(0, weight=1)

    cue_inner = ttk.Frame(cue_frame)
    cue_inner.pack(fill=tk.BOTH, expand=True)

    cue_listbox = tk.Listbox(cue_inner, selectmode=tk.EXTENDED, height=4,
                              font=("Segoe UI", 8), activestyle="none")
    cue_sb = ttk.Scrollbar(cue_inner, orient="vertical", command=cue_listbox.yview)
    cue_listbox.config(yscrollcommand=cue_sb.set)
    cue_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    cue_sb.pack(side=tk.LEFT, fill=tk.Y)

    cue_action_row = ttk.Frame(cue_frame)
    cue_action_row.pack(fill=tk.X, pady=(4, 0))
    new_style_name_var = tk.StringVar()
    ttk.Label(cue_action_row, text="Name:").pack(side=tk.LEFT)
    ttk.Entry(cue_action_row, textvariable=new_style_name_var, width=16).pack(side=tk.LEFT, padx=(4, 6))

    detected_cues = {}

    def save_selected_cues():
        sel = cue_listbox.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Select one or more cues to save.")
            return
        saved = 0
        for idx in sel:
            cue_text = cue_listbox.get(idx)
            instr    = detected_cues.get(cue_text, cue_text)
            name     = new_style_name_var.get().strip() or cue_text[:30]
            if len(sel) > 1:
                name = f"{name}_{idx+1}"
            if "style_instructions" not in app.app_config:
                app.app_config["style_instructions"] = {}
            app.app_config["style_instructions"][name] = instr
            saved += 1
        app.save_app_config()
        refresh_voice_lists()
        messagebox.showinfo("Saved", f"Saved {saved} style(s). They are now available in all tabs.")

    ttk.Button(cue_action_row, text="💾 Save Selected",
               command=save_selected_cues).pack(side=tk.LEFT)

    cue_hint = tk.Label(cue_frame, text="Run ▶ Prepare Script to detect cues.",
                        font=("Segoe UI", 8, "italic"), fg="#aaa")
    cue_hint.pack(anchor="w")

    def show_cue_frame(cues_dict):
        detected_cues.clear()
        detected_cues.update(cues_dict)
        cue_listbox.delete(0, tk.END)
        for cue in sorted(cues_dict.keys()):
            cue_listbox.insert(tk.END, cue)
        if cues_dict:
            cue_hint.pack_forget()
        else:
            cue_hint.pack(anchor="w")

    # ════════════════════════════════════════════════════════════════════════
    # ROW 1 — Full-width text input
    # ════════════════════════════════════════════════════════════════════════
    input_frame = ttk.LabelFrame(plugin_tab, text=" Input Text ", padding=6)
    input_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
    input_frame.rowconfigure(0, weight=1)
    input_frame.columnconfigure(0, weight=1)
    text_input = scrolledtext.ScrolledText(input_frame, font=("Segoe UI", 10), wrap=tk.WORD)
    text_input.grid(row=0, column=0, sticky="nsew")

    # ── Floating Preview Window (like History panel) ─────────────────────────
    preview_window   = [None]   # holds Toplevel ref
    preview_inner    = [None]   # holds inner frame ref
    preview_canvas_r = [None]   # holds canvas ref

    def open_preview_window():
        """Create or raise the floating preview Toplevel."""
        if preview_window[0] and preview_window[0].winfo_exists():
            preview_window[0].lift()
            return preview_inner[0]

        win = tk.Toplevel(app.root)
        win.title("Script Preview")
        win.geometry("400x600")
        win.configure(bg="#f4f6f9")

        # Position beside the main window
        try:
            rx = app.root.winfo_rootx()
            ry = app.root.winfo_rooty()
            rw = app.root.winfo_width()
            win.geometry(f"400x600+{rx + rw + 4}+{ry}")
        except Exception:
            win.geometry("400x600+100+100")

        # Title bar
        hdr = tk.Frame(win, bg="#2c3e50", padx=10, pady=6)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="▶ Script Preview", bg="#2c3e50", fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(hdr, text="✕", bg="#2c3e50", fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold"),
                  command=win.destroy).pack(side=tk.RIGHT)

        # Scrollable canvas
        canvas = tk.Canvas(win, bg="#f4f6f9", highlightthickness=0)
        sb     = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        inner  = tk.Frame(canvas, bg="#f4f6f9")
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        preview_window[0]   = win
        preview_inner[0]    = inner
        preview_canvas_r[0] = canvas
        return inner

    # ════════════════════════════════════════════════════════════════════════
    # ROW 2 — BOTTOM BAR (always visible)
    # ════════════════════════════════════════════════════════════════════════
    bottom_bar = tk.Frame(plugin_tab, bg="#2c3e50", padx=12, pady=10)
    bottom_bar.grid(row=2, column=0, sticky="ew")

    lbl_status = tk.Label(bottom_bar, text="Ready", bg="#2c3e50", fg="white",
                          font=("Segoe UI", 9))
    lbl_status.pack(side=tk.LEFT)

    # Send button (right) — starts disabled
    btn_send = tk.Button(bottom_bar, text="✔ Send to Batch Studio",
                         bg="#27ae60", fg="white", font=("Segoe UI", 10, "bold"),
                         bd=0, padx=14, pady=6, cursor="hand2", state=tk.DISABLED)
    btn_send.pack(side=tk.RIGHT, padx=(6, 0))

    # Re-open preview window button
    btn_show_preview = tk.Button(bottom_bar, text="🔍 Preview",
                                 bg="#5d6d7e", fg="white", font=("Segoe UI", 9, "bold"),
                                 bd=0, padx=10, pady=6, cursor="hand2")
    btn_show_preview.pack(side=tk.RIGHT, padx=4)

    # Prepare button (right)
    btn_prepare = tk.Button(bottom_bar, text="▶ Prepare Script",
                            bg="#3498db", fg="white", font=("Segoe UI", 10, "bold"),
                            bd=0, padx=14, pady=6, cursor="hand2")
    btn_prepare.pack(side=tk.RIGHT, padx=6)

    # Open file button (left)
    btn_open = tk.Button(bottom_bar, text="📂 Open File",
                         bg="#5d6d7e", fg="white", font=("Segoe UI", 9, "bold"),
                         bd=0, padx=10, pady=6, cursor="hand2")
    btn_open.pack(side=tk.LEFT, padx=(8, 0))

    # Auto-assign voices button
    btn_auto_voice = tk.Button(bottom_bar, text="🎲 Auto-assign Voices",
                               bg="#8e44ad", fg="white", font=("Segoe UI", 9, "bold"),
                               bd=0, padx=10, pady=6, cursor="hand2")
    btn_auto_voice.pack(side=tk.LEFT, padx=(8, 0))

    # ════════════════════════════════════════════════════════════════════════
    # LOGIC HELPERS
    # ════════════════════════════════════════════════════════════════════════

    # Holds the prepared script_data between Prepare and Send
    prepared_data = [None]

    # Tracks which speaker names are custom voices (not built-in)
    custom_voice_names = set()

    def refresh_voice_lists(event=None):
        """Populate all voice/style dropdowns from the app's current data."""
        bt = block_type_var.get()
        custom_voice_names.clear()
        try:
            if bt == "clone":
                speakers = app.director.get_clone_profiles()
                styles   = []
                # All clone profiles are custom
                custom_voice_names.update(speakers)
            else:
                speakers = [s for s in app.director.get_speakers() if s != "---"]
                styles   = app.director.get_styles()
                # Detect custom voices — try get_custom_voices() first, fall back
                # to checking for a "custom_voices" attribute or comparing lists
                try:
                    custom_speakers = app.director.get_custom_voices()
                    custom_voice_names.update(custom_speakers)
                except AttributeError:
                    try:
                        builtin = set(app.director.get_builtin_speakers())
                        custom_voice_names.update(s for s in speakers if s not in builtin)
                    except AttributeError:
                        pass
        except Exception as e:
            print(f"Text parser: voice refresh error: {e}")
            speakers, styles = [], []

        # Cast slots
        for sl in slots:
            sl["voice_combo"]["values"] = speakers
            sl["style_combo"]["values"] = styles
            if speakers and not sl["voice_var"].get():
                sl["voice_combo"].current(0)
            if styles and not sl["style_var"].get():
                sl["style_combo"].current(0)

        # Prose combos
        prose_voice_combo["values"] = speakers
        prose_style_combo["values"] = styles
        if speakers and not prose_voice_var.get():
            prose_voice_combo.current(0)
        if styles and not prose_style_var.get():
            prose_style_combo.current(0)

    def on_mode_change(*_):
        """Toggle cast frame vs prose frame visibility."""
        if mode_var.get() == "screenplay":
            cast_frame.grid()
            prose_frame.grid_remove()
        else:
            cast_frame.grid_remove()
            prose_frame.grid()
        prepared_data[0] = None
        btn_send.config(state=tk.DISABLED)

    mode_var.trace_add("write", on_mode_change)
    type_combo.bind("<<ComboboxSelected>>", refresh_voice_lists)

    # Initial population
    refresh_voice_lists()
    on_mode_change()

    # ── Text cleaning helper ─────────────────────────────────────────────────
    def clean_text(raw, skip_parens=False):
        """skip_parens=True keeps parens intact so screenplay cues can be extracted first."""
        t = raw
        if remove_sq_var.get():
            if sq_mode_var.get() == "all":
                t = re.sub(r'\[.*?\]', '', t)
            else:
                t = re.sub(r'\[([^\]]*?)\]', r'\1', t)  # strip brackets, keep content
        if remove_par_var.get() and not skip_parens:
            if par_mode_var.get() == "all":
                t = re.sub(r'\(.*?\)', '', t)
            else:
                t = re.sub(r'\(([^)]*?)\)', r'\1', t)   # strip parens, keep content
        if clean_sym_var.get():
            t = re.sub(r"[^\w\s.,!?'\"\-:()\[\]]", ' ', t)
            t = re.sub(r'\s+', ' ', t).strip()
        return t

    # ── Screenplay parser — supports flexible block formats ────────────────
    def parse_screenplay(raw_text):
        blocks = []
        cues_dict = {}
        chars_seen = []

        # Normalize newlines and split into paragraph chunks
        raw_text = raw_text.replace('\r\n', '\n')
        chunks = re.split(r'\n{2,}', raw_text.strip())

        # Format A: NARRATOR: [cue] text
        re_a = re.compile(r'^([A-Z][A-Z0-9 _\-]{0,29}):\s*(?:\(([^)]*)\)\s*|\[([^\]]*)\]\s*)?(.*)', re.DOTALL)
        # Format B: (Narrator) text
        re_b = re.compile(r'^\(([a-zA-Z][a-zA-Z0-9 _\-]{0,29})\)\s+(.*)', re.DOTALL)
        # Format C: Character header (with or without markdown) on line 1
        re_c_char = re.compile(r'^(?:\*\*)?([A-Za-z][A-Za-z0-9 _\-]{0,29})(?:\*\*)?[ \t]*$')
        # Format C: Cue extraction (with or without markdown)
        re_c_cue = re.compile(r'^(?:\*\*)?\[([^\]]+)\](?:\*\*)?\s*(.*)', re.DOTALL)

        last_char = ""

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk: continue

            char, cue, text = "", "", ""

            m_a = re_a.match(chunk)
            if m_a:
                char = m_a.group(1).strip().title()
                cue = (m_a.group(2) or m_a.group(3) or "").strip()
                text = m_a.group(4).strip()
            else:
                m_b = re_b.match(chunk)
                if m_b:
                    char = m_b.group(1).strip().title()
                    text = m_b.group(2).strip()
                    m_cue = re_c_cue.match(text)
                    if m_cue:
                        cue = m_cue.group(1).strip()
                        text = m_cue.group(2).strip()
                else:
                    # Check for multi-line block (Header\nDialogue)
                    lines = chunk.split('\n', 1)
                    m_c = re_c_char.match(lines[0].strip())
                    if m_c and len(lines) == 2:
                        char = m_c.group(1).strip().title()
                        text = lines[1].strip()
                        m_cue = re_c_cue.match(text)
                        if m_cue:
                            cue = m_cue.group(1).strip()
                            text = m_cue.group(2).strip()
                    elif m_c and len(lines) == 1:
                        # Edge case: Character name but dialogue is in the next chunk
                        last_char = m_c.group(1).strip().title()
                        continue

            if not char:
                # Continuation of the previous character's dialogue
                if last_char:
                    char = last_char
                    text = chunk
                    m_cue = re_c_cue.match(text)
                    if m_cue:
                        cue = m_cue.group(1).strip()
                        text = m_cue.group(2).strip()
                else:
                    continue  # Skip unassigned preamble/rules (like tag definitions)

            # Strip any lingering markdown asterisks from the dialogue
            text = text.replace('**', '')
            last_char = char

            if char not in chars_seen:
                chars_seen.append(char)
            if cue:
                cues_dict[cue] = cue
            
            blocks.append({"char": char, "cue": cue, "text": text})

        return blocks, cues_dict, chars_seen

    # ── Auto-detect screenplay format ────────────────────────────────────────
    def auto_detect_mode(text):
        blocks, _, _ = parse_screenplay(text)
        mode_var.set("screenplay" if len(blocks) > 0 else "prose")

    def split_to_word_limit(text, limit):
        """Split text into chunks respecting sentence boundaries, <= limit words."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks, current, count = [], [], 0
        for s in sentences:
            wc = len(s.split())
            if count + wc <= limit:
                current.append(s)
                count += wc
            else:
                if current:
                    chunks.append(" ".join(current))
                # If single sentence is too long, chunk by word count
                if wc > limit:
                    words = s.split()
                    for i in range(0, len(words), limit):
                        chunks.append(" ".join(words[i:i+limit]))
                    current, count = [], 0
                else:
                    current, count = [s], wc
        if current:
            chunks.append(" ".join(current))
        return chunks

    # ── Build script_data from screenplay blocks ─────────────────────────────
    def build_screenplay_script(blocks, chars_found):
        bt      = block_type_var.get()
        temp    = temp_var.get()
        top_p   = top_p_var.get()
        limit   = max_words_var.get()
        styles  = app.director.get_styles()

        # Build char→slot map
        char_to_slot = {}
        for i, sl in enumerate(slots):
            cname = sl["char_var"].get().strip().title()
            if cname and cname not in ("Character 1", "Character 2", "Character 3"):
                char_to_slot[cname] = i
        # Also try auto-matching by order of appearance
        for ci, ch in enumerate(chars_found[:3]):
            if ch not in char_to_slot:
                char_to_slot[ch] = ci

        script_data = []
        for b in blocks:
            slot_idx = char_to_slot.get(b["char"], 0)
            sl       = slots[slot_idx]
            voice    = sl["voice_var"].get()
            style    = sl["style_var"].get()
            lang_sel = sl["lang_var"].get()
            language = "" if lang_sel == "Auto" else lang_sel
            is_custom = (voice in custom_voice_names) or (bt == "clone")

            # If cue matches a saved style, use it
            if b["cue"] and b["cue"] in styles:
                style = b["cue"]

            for chunk in split_to_word_limit(b["text"], limit):
                entry = {
                    "type": bt, "speaker": voice,
                    "text": chunk, "language": language,
                    "temp": temp, "top_p": top_p,
                    "_char": b["char"], "_cue": b["cue"],
                    "_slot": slot_idx,
                }
                if is_custom:
                    entry["custom"] = True
                if bt == "standard":
                    entry["style"] = style
                script_data.append(entry)
        return script_data

    # ── Build script_data from prose ─────────────────────────────────────────
    def build_prose_script(text):
        bt      = block_type_var.get()
        temp    = temp_var.get()
        top_p   = top_p_var.get()
        limit   = max_words_var.get()
        voice   = prose_voice_var.get()
        style   = prose_style_var.get()
        lang_sel = prose_lang_var.get()
        language = "" if lang_sel == "Auto" else lang_sel
        is_custom = (voice in custom_voice_names) or (bt == "clone")

        chunks = split_to_word_limit(text, limit)
        script_data = []
        for chunk in chunks:
            entry = {
                "type": bt, "speaker": voice,
                "text": chunk, "language": language,
                "temp": temp, "top_p": top_p,
                "_char": "Narrator", "_cue": "", "_slot": 0,
            }
            if is_custom:
                entry["custom"] = True
            if bt == "standard":
                entry["style"] = style
            script_data.append(entry)
        return script_data

    # ── PREVIEW RENDERER ─────────────────────────────────────────────────────
    def render_preview(script_data):
        inner = open_preview_window()

        # Clear old widgets
        for w in inner.winfo_children():
            w.destroy()

        if not script_data:
            tk.Label(inner, text="Nothing to preview.",
                     font=("Segoe UI", 9, "italic"), fg="#aaa",
                     bg="#f4f6f9").pack(pady=20)
            return

        tk.Label(inner,
                 text=f"{len(script_data)} blocks",
                 font=("Segoe UI", 8, "bold"), fg="#888",
                 bg="#f4f6f9").pack(anchor="w", padx=6, pady=(4, 2))

        # Work out wraplength from window width
        try:
            ww = preview_window[0].winfo_width() - 40
            if ww < 100: ww = 360
        except Exception:
            ww = 360

        for i, entry in enumerate(script_data):
            slot = entry.get("_slot", 0)
            bg   = CHAR_COLORS[min(slot, 2)]
            fg   = CHAR_TEXT[min(slot, 2)]

            card = tk.Frame(inner, bg=bg, bd=1, relief="solid", pady=4, padx=6)
            card.pack(fill=tk.X, padx=6, pady=2)

            hdr = tk.Frame(card, bg=bg)
            hdr.pack(fill=tk.X)

            tk.Label(hdr, text=f"#{i+1}", bg=bg, fg=fg,
                     font=("Consolas", 7, "bold"), width=4, anchor="w").pack(side=tk.LEFT)
            tk.Label(hdr, text=entry.get("_char", ""),
                     bg=bg, fg=fg, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(2, 6))
            tk.Label(hdr, text=f"🎙 {entry['speaker']}",
                     bg=bg, fg="#555", font=("Segoe UI", 7)).pack(side=tk.LEFT)

            cue = entry.get("_cue", "")
            if cue:
                tk.Label(hdr, text=f"({cue})", bg=bg,
                         fg="#888", font=("Segoe UI", 7, "italic")).pack(side=tk.LEFT, padx=4)

            wc = len(entry["text"].split())
            tk.Label(hdr, text=f"{wc}w", bg=bg, fg="#aaa",
                     font=("Consolas", 7)).pack(side=tk.RIGHT)

            tk.Label(card, text=entry["text"], bg=bg, fg="#333",
                     font=("Segoe UI", 9), wraplength=ww,
                     justify="left", anchor="w").pack(fill=tk.X, pady=(2, 0))

    # ── OPEN FILE ────────────────────────────────────────────────────────────
    def open_file():
        path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not path:
            return
        # Try encodings in order — utf-8, then Windows-1252 (handles Ox97 em-dash etc.), then latin-1
        content = None
        for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if content is None:
            messagebox.showerror("Error", "Could not decode the file with any supported encoding.")
            return
        text_input.delete("1.0", tk.END)
        text_input.insert("1.0", content)
        auto_detect_mode(content)
        lbl_status.config(text=f"Loaded: {os.path.basename(path)}")
        # Reset prepared state
        prepared_data[0] = None
        btn_send.config(state=tk.DISABLED)

    btn_open.config(command=open_file)

    # ── PREPARE SCRIPT ───────────────────────────────────────────────────────
    def auto_assign_voices(chars_found):
        """
        Intelligently assign available app voices to the 3 character slots.
        Strategy (in order):
          1. Exact name match  (e.g. character "Ryan"  -> preset "Ryan")
          2. Partial name match
          3. Gender/role heuristics from character name keywords
          4. Round-robin from remaining voices
        """
        try:
            available = [s for s in app.director.get_speakers() if s != "---"]
        except Exception:
            return
        if not available:
            return

        FEMALE_VOICES = {"vivian", "serena", "sohee", "ono_anna", "anna"}
        MALE_VOICES   = {"ryan", "aiden", "eric", "dylan", "uncle_fu"}
        FEMALE_HINTS  = {"elena", "emma", "sara", "lily", "anna", "marie", "alice",
                         "julia", "isabella", "she", "her", "lady", "queen",
                         "princess", "woman", "girl", "mother", "wife"}
        MALE_HINTS    = {"marcus", "james", "john", "david", "oliver", "william",
                         "he", "him", "lord", "king", "prince", "man", "boy",
                         "father", "husband", "uncle", "narrator"}

        avail_lower = {v.split("(")[0].strip().lower(): v for v in available}
        used = set()

        for i, char in enumerate(chars_found[:3]):
            char_l     = char.lower().replace(" ", "_")
            char_words = set(char_l.replace("_", " ").split())
            assigned   = None

            # 1. Exact match
            for vl, v in avail_lower.items():
                if char_l == vl and v not in used:
                    assigned = v
                    break

            # 2. Partial match
            if not assigned:
                for vl, v in avail_lower.items():
                    if (char_l in vl or vl in char_l) and v not in used:
                        assigned = v
                        break

            # 3. Gender / role heuristics
            if not assigned:
                is_female = bool(char_words & FEMALE_HINTS)
                is_male   = bool(char_words & MALE_HINTS)
                if is_female:
                    pool = [v for vl, v in avail_lower.items()
                            if vl in FEMALE_VOICES and v not in used]
                elif is_male:
                    pool = [v for vl, v in avail_lower.items()
                            if vl in MALE_VOICES and v not in used]
                else:
                    pool = []
                if not pool:
                    pool = [v for v in available if v not in used]
                if pool:
                    assigned = pool[0]

            # 4. Fallback round-robin
            if not assigned:
                for v in available:
                    if v not in used:
                        assigned = v
                        break

            if assigned:
                slots[i]["voice_var"].set(assigned)
                used.add(assigned)

        lbl_status.config(text="Voices auto-assigned — review the Cast panel and adjust if needed.")

    def prepare_script():
        raw = text_input.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Empty", "Please paste or load text first.")
            return

        if mode_var.get() == "screenplay":
            # Parse on raw text so parens (stage cues) are preserved for extraction
            blocks, cues_dict, chars_found = parse_screenplay(raw)

            if not blocks:
                messagebox.showwarning(
                    "No blocks found",
                    "No screenplay lines detected (expected format: CHARACTER: text).\n"
                    "Try switching to Prose mode.")
                return

            # Clean each block's dialogue text individually (skip_parens already extracted)
            for b in blocks:
                b["text"] = clean_text(b["text"], skip_parens=False)

            # Auto-fill character name slots
            for i, ch in enumerate(chars_found[:3]):
                slots[i]["char_var"].set(ch)

            # Auto-assign voices when slots are still at defaults
            slot_voices = [sl["voice_var"].get() for sl in slots]
            if not any(slot_voices):
                auto_assign_voices(chars_found)

            show_cue_frame(cues_dict)
            script_data = build_screenplay_script(blocks, chars_found)

        else:  # prose
            cleaned = clean_text(raw)
            show_cue_frame({})
            script_data = build_prose_script(cleaned)

        if not script_data:
            messagebox.showwarning("Warning", "No blocks generated.")
            return

        prepared_data[0] = script_data
        render_preview(script_data)
        btn_send.config(state=tk.NORMAL)
        lbl_status.config(
            text=f"Preview ready — {len(script_data)} blocks. Click ✔ Send to load into Batch Studio.")

    btn_prepare.config(command=prepare_script)
    btn_show_preview.config(command=open_preview_window)
    btn_auto_voice.config(command=lambda: auto_assign_voices(
        [sl["char_var"].get() for sl in slots]))

    # ── SEND TO BATCH STUDIO ─────────────────────────────────────────────────
    def send_to_batch():
        data = prepared_data[0]
        if not data:
            messagebox.showwarning("Nothing prepared",
                                   "Click ▶ Prepare Script first.")
            return

        # Strip internal preview keys before sending
        clean_data = []
        for entry in data:
            clean_data.append({k: v for k, v in entry.items()
                                if not k.startswith("_")})

        n = len(clean_data)
        if not messagebox.askyesno(
                "Confirm",
                f"Load {n} blocks into Batch Studio?\nThis will replace the current scene."):
            return

        try:
            app.director.load_script_data(clean_data, name="Parsed Script")
            app.notebook.select(app.tab_batch)
            lbl_status.config(text=f"✔ Sent {n} blocks to Batch Studio.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send to Batch Studio:\n{e}")

    btn_send.config(command=send_to_batch)