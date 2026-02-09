# 🔌 Qwen3-TTS Plugin System (Developer Guide)

The Qwen3-TTS Pro Suite is designed to be extensible. You can add entirely new features, tabs, or automation scripts without modifying the core application code.

---

## 🛠️ How it Works
On startup, the application scans the `./modules/` folder. The **Module Hub** then checks the `enabled_modules.json` registry to determine which plugins should be initialized.

### The Module Hub (Settings)
Starting in v3.9.0, you can manage your plugins via the **Settings -> Module Hub** tab:
*   **Synchronize**: Pulls the latest official plugins from the GitHub repository.
*   **Toggle**: Enable or disable plugins without deleting the files.
*   **Validation**: The Hub automatically verifies that the plugin contains the required `initialize(app)` header.

### The Plugin Interface
Every plugin must define an `initialize(app)` function. This function is called by the main application and receives the `app` instance (the `QwenTTSApp` object), giving you full control over the suite.

```python
def initialize(app):
    # Your code starts here
    print("My Plugin Loaded!")
```

---

## 🚀 Creating your first Plugin (Hello World)

Create a file named `hello_plugin.py` in the `modules/` folder:

```python
import tkinter as tk
from tkinter import ttk

def initialize(app):
    # 1. Add a new tab to the main window
    plugin_tab = ttk.Frame(app.notebook)
    app.notebook.add(plugin_tab, text="👋 Hello")

    # 2. Add some UI
    label = tk.Label(plugin_tab, text="Hello from my Plugin!", font=("Segoe UI", 12))
    label.pack(pady=20)

    # 3. Create a button that uses the main app's engine
    def say_hello():
        app.speaker_var.set("Aiden (English Male)")
        app.text_input_custom.delete("1.0", tk.END)
        app.text_input_custom.insert("1.0", "Hello! I am being controlled by an external plugin.")
        app.start_gen_custom()

    ttk.Button(plugin_tab, text="Run Engine", command=say_hello).pack()
```

---

## 🤖 The "Auto-Script" Tab
The "Auto-Script" tab visible in the application is a **demonstration plugin** (located in `./modules/tutorial_plugin.py`). It serves two purposes:
1. It shows users how an automated workflow looks.
2. It provides developers with a reference implementation for controlling the engine via scripts.

---

## ☁️ Headless Plugins & Background Services
Plugins do **not** have to create a visible tab. They can run entirely in the background. Possible "Smarter" implementations include:

*   **Watch Folders:** A plugin that monitors a specific folder for `.json` script files. When a file is dropped in, the plugin automatically triggers the engine and saves the audio, without any user interaction required.
*   **Local HTTP API:** A plugin can start a micro-webserver (like FastAPI or Flask) inside the app. This allows other applications (games, web apps, or automation tools) to send generation requests directly to Qwen3 Studio via standard web requests.
*   **Context Menu Extensions:** Adding new right-click options to the "Session History" list to send audio to external editors or cloud storage.

---

## 🤖 Automated Scripting & Callbacks
Starting in v3.6.2, the generation methods support **callbacks**. This allows your plugin to run a sequence of generations automatically.

### Example: The `on_complete` system
```python
def run_automation(app):
    def on_finished(result):
        if result["status"] == "success":
            print(f"Generation finished in {result['duration']}s")
            # You can now trigger the next line or process the audio
        else:
            print(f"Error: {result['message']}")

    # Trigger generation with a callback
    app.start_gen_custom(on_complete=on_finished)
```

**The `result` dictionary contains:**
*   `status`: "success" or "error"
*   `audio`: The raw numpy waveform data.
*   `sample_rate`: The sample rate of the audio.
*   `duration`: Time taken to generate.
*   `mode`: Which engine was used ("custom", "design", or "base").

---

## 🔑 Key `app` Attributes you can access:
*   `app.notebook`: The main UI tab container.
*   `app.model`: The currently loaded AI model.
*   `app.root`: The main Tkinter window.
*   `app.speaker_var`: The variable controlling the Custom Voice dropdown.
*   `app.ensure_model(mode)`: Call this to check/switch engines automatically.

---
© 2026 Blues Creative Engineering.
