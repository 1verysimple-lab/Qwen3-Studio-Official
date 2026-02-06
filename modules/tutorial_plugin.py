import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

def initialize(app):
    """
    Automated Scripting Demo Plugin.
    Shows how a module can run a sequence of generations automatically.
    """
    plugin_tab = ttk.Frame(app.notebook)
    app.notebook.add(plugin_tab, text="🤖 Auto-Script")
    
    tk.Label(plugin_tab, text="Automated Scripting Module", font=("Segoe UI", 14, "bold")).pack(pady=20)
    
    log_text = tk.Text(plugin_tab, height=10, width=60, font=("Consolas", 9))
    log_text.pack(padx=20, pady=10)
    
    def log(msg):
        log_text.insert(tk.END, f"{msg}\n")
        log_text.see(tk.END)

    script = [
        {"voice": "Aiden (English Male)", "text": "Starting the automated sequence. Step one is complete."},
        {"voice": "Serena (Chinese Female)", "text": "Step two. I am now speaking in a different voice automatically."},
        {"voice": "Ryan (English Male)", "text": "Sequence complete. The module has successfully controlled the engine."}
    ]

    def run_automated_script():
        log("--- Starting Auto-Script ---")
        
        def process_next(index):
            if index >= len(script):
                log("--- All Tasks Finished ---")
                return

            item = script[index]
            log(f"Processing {index+1}/{len(script)}: {item['voice']}")
            
            # 1. Setup the main app's UI state
            app.speaker_var.set(item['voice'])
            app.text_input_custom.delete("1.0", tk.END)
            app.text_input_custom.insert("1.0", item['text'])
            
            # 2. Define what happens when THIS specific generation is done
            def on_finished(result):
                if result["status"] == "success":
                    log(f"   Success! (Duration: {result['duration']:.2f}s)")
                    # Wait a small bit before the next one for natural feel
                    time.sleep(1) 
                    process_next(index + 1)
                else:
                    log(f"   Error: {result.get('message')}")

            # 3. Trigger the generation with our callback
            app.start_gen_custom(on_complete=on_finished)

        # Start the recursive chain in a background thread so we don't freeze the UI
        threading.Thread(target=lambda: process_next(0), daemon=True).start()

    btn = ttk.Button(plugin_tab, text="🎬 Run Automated Script", command=run_automated_script)
    btn.pack(pady=20)