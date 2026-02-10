import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import re
import os

def initialize(app):
    """
    Text Parser Plugin for Qwen3-TTS.
    Parses long text files into manageable blocks for the Batch Studio.
    Includes text cleaning options and long-sentence refinement.
    """
    plugin_tab = ttk.Frame(app.notebook)
    app.notebook.add(plugin_tab, text="Text Parser")

    # --- UI Layout ---
    main_frame = ttk.Frame(plugin_tab, padding=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(main_frame, text="Text to Batch Script Parser", font=("Segoe UI", 14, "bold")).pack(pady=(0, 5))
    tk.Label(main_frame, text="Convert long documents into individual batch blocks automatically.", font=("Segoe UI", 10)).pack(pady=(0, 15))

    # Controls Frame
    ctrl_frame = ttk.LabelFrame(main_frame, text="Generation Options", padding=15)
    ctrl_frame.pack(fill=tk.X, pady=(0, 10))

    # Row 0: Block Type & Max Words
    ttk.Label(ctrl_frame, text="Block Type:").grid(row=0, column=0, sticky="w")
    block_type_var = tk.StringVar(value="standard")
    type_combo = ttk.Combobox(ctrl_frame, textvariable=block_type_var, values=["standard", "clone"], state="readonly", width=10)
    type_combo.grid(row=0, column=1, sticky="w", padx=10)

    ttk.Label(ctrl_frame, text="Max Words per Block:").grid(row=0, column=2, sticky="w", padx=(20, 0))
    max_words_var = tk.IntVar(value=30)
    max_words_spin = ttk.Spinbox(ctrl_frame, from_=5, to=100, textvariable=max_words_var, width=5)
    max_words_spin.grid(row=0, column=3, sticky="w", padx=10)
    
    # Row 1: Default Voice
    ttk.Label(ctrl_frame, text="Default Voice:").grid(row=1, column=0, sticky="w", pady=10)
    default_voice_var = tk.StringVar()
    voice_combo = ttk.Combobox(ctrl_frame, textvariable=default_voice_var, state="readonly", width=25)
    voice_combo.grid(row=1, column=1, columnspan=3, sticky="w", padx=10)

    # Row 2: Default Style (Only for Standard)
    lbl_style = ttk.Label(ctrl_frame, text="Default Style:")
    default_style_var = tk.StringVar()
    style_combo = ttk.Combobox(ctrl_frame, textvariable=default_style_var, state="readonly", width=25)

    # Row 3: Precision Controls
    prec_frame = ttk.Frame(ctrl_frame)
    prec_frame.grid(row=3, column=0, columnspan=4, sticky="w", pady=(5, 0))
    
    ttk.Label(prec_frame, text="Temperature:").pack(side=tk.LEFT)
    temp_var = tk.DoubleVar(value=0.8)
    ttk.Spinbox(prec_frame, from_=0.1, to=1.5, increment=0.1, textvariable=temp_var, width=5).pack(side=tk.LEFT, padx=(5, 20))
    
    ttk.Label(prec_frame, text="Top P:").pack(side=tk.LEFT)
    top_p_var = tk.DoubleVar(value=0.8)
    ttk.Spinbox(prec_frame, from_=0.1, to=1.0, increment=0.1, textvariable=top_p_var, width=5).pack(side=tk.LEFT, padx=5)

    # Cleaning Frame
    clean_frame = ttk.LabelFrame(main_frame, text="Cleaning Options", padding=15)
    clean_frame.pack(fill=tk.X, pady=(0, 15))

    remove_sq_brackets_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(clean_frame, text="Remove [content inside]", variable=remove_sq_brackets_var).grid(row=0, column=0, sticky="w", padx=5)

    remove_parens_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(clean_frame, text="Remove (content inside)", variable=remove_parens_var).grid(row=0, column=1, sticky="w", padx=20)

    clean_symbols_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(clean_frame, text="Clean Special Symbols", variable=clean_symbols_var).grid(row=0, column=2, sticky="w", padx=5)

    def update_voice_list(event=None):
        block_type = block_type_var.get()
        try:
            if block_type == "clone":
                available_speakers = app.director.get_clone_profiles()
                lbl_style.grid_remove()
                style_combo.grid_remove()
            else:
                available_speakers = app.director.get_speakers()
                available_speakers = [s for s in available_speakers if s != "---"]
                lbl_style.grid(row=2, column=0, sticky="w", pady=(0, 10))
                style_combo.grid(row=2, column=1, columnspan=3, sticky="w", padx=10, pady=(0, 10))
                styles = app.director.get_styles()
                style_combo['values'] = styles
                if styles: 
                    if "News Anchor" in styles: default_style_var.set("News Anchor")
                    else: style_combo.current(0)
                else:
                    default_style_var.set("")

            voice_combo['values'] = available_speakers
            if available_speakers:
                if "Aiden" in available_speakers and block_type == "standard":
                    default_voice_var.set("Aiden")
                else:
                    voice_combo.current(0)
            else:
                default_voice_var.set("")
        except Exception as e:
            print(f"Error updating voice list: {e}")

    type_combo.bind("<<ComboboxSelected>>", update_voice_list)
    update_voice_list() # Initial population

    # Input Area
    ttk.Label(main_frame, text="Input Text:").pack(anchor="w")
    text_input = scrolledtext.ScrolledText(main_frame, height=10, font=("Segoe UI", 10), wrap=tk.WORD)
    text_input.pack(fill=tk.BOTH, expand=True, pady=(5, 15))

    # Buttons
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill=tk.X)

    def open_file():
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                text_input.delete("1.0", tk.END)
                text_input.insert("1.0", content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file:\n{e}")

    ttk.Button(btn_frame, text="Open Text File", command=open_file, style="Big.TButton").pack(side=tk.LEFT, padx=(0, 10))

    def show_refinement_dialog(long_sentences, on_confirm):
        """Allows manual split of sentences that exceed max_words."""
        d = tk.Toplevel(app.root)
        d.title("Sentence Refinement Required")
        d.geometry("600x500")
        d.transient(app.root)
        d.grab_set()

        tk.Label(d, text="Long Sentences Detected", font=("Segoe UI", 12, "bold"), pady=10).pack()
        tk.Label(d, text=f"The following sentences exceed your {max_words_var.get()} word limit.\nPlease split them manually using [SPLIT] markers or punctuation.", 
                 font=("Segoe UI", 9), wraplength=550).pack(pady=(0, 10))

        # List Area
        container = tk.Frame(d)
        container.pack(fill=tk.BOTH, expand=True, padx=20)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_f = tk.Frame(canvas)
        
        scroll_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_f, anchor="nw", width=540)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text_widgets = []
        for i, sent in enumerate(long_sentences):
            f = tk.Frame(scroll_f, pady=10)
            f.pack(fill=tk.X)
            tk.Label(f, text=f"Sentence {i+1} ({len(sent.split())} words):", font=("Segoe UI", 9, "bold")).pack(anchor="w")
            txt = scrolledtext.ScrolledText(f, height=4, font=("Segoe UI", 10), wrap=tk.WORD)
            txt.pack(fill=tk.X, pady=2)
            txt.insert("1.0", sent)
            text_widgets.append(txt)
            ttk.Separator(scroll_f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        def confirm():
            refined_parts = []
            for txt in text_widgets:
                val = txt.get("1.0", tk.END).strip()
                # Split by [SPLIT] marker or punctuation
                # We replace [SPLIT] with a period temporarily for the secondary parser
                val = val.replace("[SPLIT]", ".")
                # Re-parse this refined sentence
                sub_parts = re.split(r'(?<=[.!?])\s+', val)
                refined_parts.extend([p.strip() for p in sub_parts if p.strip()])
            
            d.destroy()
            on_confirm(refined_parts)

        def auto_split():
            if messagebox.askyesno("Auto Split", "Automatically split these sentences by word count? (May cut mid-sentence)"):
                refined_parts = []
                limit = max_words_var.get()
                for txt in text_widgets:
                    val = txt.get("1.0", tk.END).strip()
                    words = val.split()
                    for i in range(0, len(words), limit):
                        refined_parts.append(" ".join(words[i:i+limit]))
                d.destroy()
                on_confirm(refined_parts)

        btn_f = tk.Frame(d, pady=15)
        btn_f.pack(fill=tk.X)
        ttk.Button(btn_f, text="Auto-Split All", command=auto_split).pack(side=tk.LEFT, padx=20)
        ttk.Button(btn_f, text="Apply Refined Splits", command=confirm).pack(side=tk.RIGHT, padx=20)

    def parse_and_send():
        raw_text = text_input.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("Warning", "Please enter or load some text first.")
            return

        # --- Cleaning Logic ---
        cleaned_text = raw_text
        if remove_sq_brackets_var.get():
            cleaned_text = re.sub(r'\[.*?\]', '', cleaned_text)
        if remove_parens_var.get():
            cleaned_text = re.sub(r'\(.*?\)', '', cleaned_text)
        if clean_symbols_var.get():
            cleaned_text = re.sub(r"[^\w\s.,!?'\"-]", ' ', cleaned_text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        if not cleaned_text:
            messagebox.showwarning("Warning", "Cleaning resulted in empty text.")
            return

        max_words = max_words_var.get()
        
        # --- Parsing Logic Phase 1: Identify Long Sentences ---
        initial_parts = re.split(r'(?<=[.!?])\s+', cleaned_text)
        
        final_parts = []
        long_sentences = []
        
        for part in initial_parts:
            part = part.strip()
            if not part: continue
            if len(part.split()) > max_words:
                long_sentences.append(part)
            else:
                final_parts.append(part)

        def proceed_with_blocks(refined_sentences=None):
            all_sentences = final_parts + (refined_sentences if refined_sentences else [])
            
            # Sort back into relative order or just append? 
            # For simplicity, we'll append. If order is critical, we'd need a more complex tracker.
            # However, usually users refine the text globally.
            
            # Re-running the grouping logic on all final sentences
            script_data = []
            current_block_text = []
            current_word_count = 0

            speaker = default_voice_var.get()
            block_type = block_type_var.get()
            style = default_style_var.get()
            temp = temp_var.get()
            top_p = top_p_var.get()

            def add_script_block(text):
                block = {
                    "type": block_type, "speaker": speaker, "text": text,
                    "language": "English", "temp": temp, "top_p": top_p
                }
                if block_type == "standard": block["style"] = style
                script_data.append(block)

            # NOTE: To maintain order, we must process the ORIGINAL initial_parts list 
            # and replace the long ones with their refined versions as we go.
            
            ordered_sentences = []
            refined_idx = 0
            for part in initial_parts:
                part = part.strip()
                if not part: continue
                if len(part.split()) > max_words:
                    # This was a long sentence, we need to add the refined segments for it
                    # (Refined sentences are stored flat in refined_sentences)
                    # We need to find which refined parts belong to this original long sentence.
                    # Since refined_sentences is a flat list of ALL refined segments:
                    # This logic is simpler if we refine sentence by sentence.
                    pass

            # Simpler implementation: Just use the initial_parts and handle the refined ones
            # during the main loop.
            
            for part in initial_parts:
                part = part.strip()
                if not part: continue
                
                # Check if this was one of the long ones
                if len(part.split()) > max_words:
                    # In a real production, we'd map refined segments back.
                    # Here we just use the refined flat list we got back.
                    # Since we don't have a map, we'll just process the refined list separately 
                    # OR we change the dialog to return a map.
                    pass

            # REVISED LOGIC: If refined_sentences is provided, it means we've already 
            # broken down the long ones. Let's rebuild the sequence.
            
            processed_sequence = []
            for part in initial_parts:
                part = part.strip()
                if not part: continue
                if len(part.split()) > max_words:
                    # Find refined segments for this specific sentence
                    # (This is why we'll just use the flat list for now for simplicity)
                    pass
            
            # FLAT RECONSTRUCTION (Simplest for now)
            # We'll just group all current final_parts + refined_sentences
            # but users expect order. Let's fix the dialog to keep order.
            
            # FINAL GROUPING
            # We'll re-run the grouping logic on a list that contains 
            # either the original short sentence or the multiple refined segments.
            
            full_sentence_list = []
            long_ptr = 0
            for part in initial_parts:
                part = part.strip()
                if not part: continue
                if len(part.split()) > max_words:
                    # This sentence was refined. How many segments?
                    # We need to know which segments came from which sentence.
                    # We'll handle this by passing a list of lists to the confirm callback.
                    full_sentence_list.extend(refined_sentences[long_ptr])
                    long_ptr += 1
                else:
                    full_sentence_list.append(part)

            for s in full_sentence_list:
                words_in_s = s.split()
                count_in_s = len(words_in_s)
                
                if current_word_count + count_in_s <= max_words:
                    current_block_text.append(s)
                    current_word_count += count_in_s
                else:
                    if current_block_text:
                        add_script_block(" ".join(current_block_text))
                    current_block_text = [s]
                    current_word_count = count_in_s

            if current_block_text:
                add_script_block(" ".join(current_block_text))

            if not script_data:
                messagebox.showwarning("Warning", "No blocks generated.")
                return

            if messagebox.askyesno("Confirm", f"This will clear the current Batch Studio and load {len(script_data)} blocks ({block_type}). Continue?"):
                try:
                    app.director.load_script_data(script_data, name="Parsed Text")
                    app.notebook.select(app.tab_batch)
                    messagebox.showinfo("Success", f"Loaded {len(script_data)} blocks into Batch Studio.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load data into Batch Studio:\n{e}")

        if long_sentences:
            # We need to change the callback to handle nested lists to maintain order
            def on_refined(nested_refined_list):
                proceed_with_blocks(nested_refined_list)
            
            # Redefining the dialog internally to return nested list
            def show_refinement_dialog_v2(sentences, on_confirm):
                d = tk.Toplevel(app.root)
                d.title("Sentence Refinement Required")
                d.geometry("600x600")
                d.transient(app.root)
                d.grab_set()
                tk.Label(d, text="Split Long Sentences", font=("Segoe UI", 12, "bold"), pady=10).pack()
                
                container = tk.Frame(d)
                container.pack(fill=tk.BOTH, expand=True, padx=20)
                canvas = tk.Canvas(container, highlightthickness=0); scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
                scroll_f = tk.Frame(canvas); scroll_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                canvas.create_window((0, 0), window=scroll_f, anchor="nw", width=540); canvas.configure(yscrollcommand=scroll.set)
                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); scroll.pack(side=tk.RIGHT, fill=tk.Y)

                text_widgets = []
                for i, sent in enumerate(sentences):
                    f = tk.Frame(scroll_f, pady=10); f.pack(fill=tk.X)
                    tk.Label(f, text=f"Sentence {i+1} ({len(sent.split())} words):", font=("Segoe UI", 9, "bold")).pack(anchor="w")
                    txt = scrolledtext.ScrolledText(f, height=4, font=("Segoe UI", 10), wrap=tk.WORD); txt.pack(fill=tk.X, pady=2); txt.insert("1.0", sent)
                    text_widgets.append(txt); ttk.Separator(scroll_f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

                def confirm():
                    nested_refined = []
                    for x in text_widgets:
                        val = x.get("1.0", tk.END).strip().replace("[SPLIT]", ".")
                        sub = [p.strip() for p in re.split(r'(?<=[.!?])\s+', val) if p.strip()]
                        nested_refined.append(sub)
                    d.destroy(); on_confirm(nested_refined)

                def auto():
                    nested_refined = []
                    limit = max_words_var.get()
                    for x in text_widgets:
                        val = x.get("1.0", tk.END).strip(); words = val.split()
                        sub = [" ".join(words[i:i+limit]) for i in range(0, len(words), limit)]
                        nested_refined.append(sub)
                    d.destroy(); on_confirm(nested_refined)

                btn_f = tk.Frame(d, pady=15); btn_f.pack(fill=tk.X)
                ttk.Button(btn_f, text="Auto-Split All", command=auto).pack(side=tk.LEFT, padx=20)
                ttk.Button(btn_f, text="Apply Refined Splits", command=confirm).pack(side=tk.RIGHT, padx=20)

            show_refinement_dialog_v2(long_sentences, on_refined)
        else:
            # No long sentences, proceed directly
            # We need a dummy nested list that is empty
            proceed_with_blocks([])

    ttk.Button(btn_frame, text="Send to Batch Studio", command=parse_and_send, style="Big.TButton").pack(side=tk.LEFT)

    # Style for the big button
    s = ttk.Style()
    s.configure("Big.TButton", font=("Segoe UI", 10, "bold"), padding=10)
