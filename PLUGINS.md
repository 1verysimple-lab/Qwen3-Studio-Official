# 🔌 Qwen3-TTS Plugin System (Developer Guide)

The Qwen3-TTS Pro Suite is designed to be extensible. You can add new features, tabs, or automation services without modifying the core application code.

---

## 🛠️ How It Works

On startup, the application scans the `./modules/` folder. The **Module Hub** checks `enabled_modules.json` to determine which plugins should be initialised. Plugins that fail to load are logged and skipped — a broken plugin does not crash the app.

### The Modules Manager Tab
* **Synchronise**: Pulls the latest official plugins from the GitHub repository.
* **Toggle**: Enable or disable plugins without deleting the files. Takes effect immediately — no restart required.
* **Validation**: The Hub verifies each plugin contains the required `initialize(app)` function before loading.

### The Plugin Interface

Every plugin must define a single top-level function:

```python
def initialize(app):
    # app is the QwenTTSApp instance
    # Called once at startup after the main UI is fully built
    print("My plugin loaded!")
```

---

## 📦 Bundled Plugins

| Plugin File | Status | Description |
| :--- | :--- | :--- |
| `tutorial_plugin.py` | Enabled | Interactive multi-chapter tutorial experience. |
| `peak_meter_plugin.py` | Enabled | Floating real-time peak meter (📶 VU button in header). |
| `style_profile_manager_plugin.py` | Enabled | Manage, enable/disable, and inline-edit Styles and Voice Design Profiles. |
| `text_parser_plugin.py` | Enabled | Script Helper tab for splitting and cleaning long texts. |
| `autoscript_plugin.py` | Disabled | Demo plugin showing external automation control of the engine. |

---

## 🏗️ Creating Your First Plugin (Hello World)

Create `modules/hello_plugin.py`:

```python
import tkinter as tk
from tkinter import ttk

def initialize(app):
    # Add a new tab to the main window
    plugin_tab = ttk.Frame(app.notebook)
    app.notebook.add(plugin_tab, text="Hello")

    # Add some UI
    tk.Label(plugin_tab, text="Hello from my Plugin!", font=("Segoe UI", 12)).pack(pady=20)

    # Trigger a generation from the plugin
    def say_hello():
        app.speaker_var.set("Aiden")
        app.text_input_custom.delete("1.0", tk.END)
        app.text_input_custom.insert("1.0", "Hello, I am being controlled by an external plugin.")
        app.start_gen_custom()

    ttk.Button(plugin_tab, text="Run Engine", command=say_hello).pack()
```

Enable it from the **Modules** tab and it appears immediately.

---

## 🤖 Headless Plugins & Background Services

Plugins do **not** need to create a visible tab. They can run entirely in the background. Use cases:

* **Watch Folder**: Monitor a folder for `.txt` files and automatically trigger generation when one is dropped in.
* **Local HTTP API**: Start a micro-server (FastAPI/Flask) inside the app so other applications can request audio via HTTP.
* **Custom Exporter**: Push finished audio directly to a game engine, DAW, or cloud storage after each batch block completes.
* **Context Menu Extension**: Add right-click options to the Session History list.

---

## 🔑 Key `app` Attributes

### UI & Core
| Attribute | Type | Description |
| :--- | :--- | :--- |
| `app.root` | `tk.Tk` | The main Tkinter window. |
| `app.notebook` | `ttk.Notebook` | Main tab container. Add your plugin tab here. |
| `app.colors` | `dict` | Theme colour palette. Use `app.colors["accent"]`, `app.colors["bg"]`, etc. |

### Engine & Model
| Attribute | Type | Description |
| :--- | :--- | :--- |
| `app.model` | `Qwen3TTSModel` or `None` | The currently loaded inference model. |
| `app.current_model_type` | `str` | `"custom"`, `"design"`, or `"base"`. |
| `app.switch_model(mtype)` | method | Switches to the specified engine type asynchronously. |
| `app.flush_vram()` | method | Runs `gc.collect()` + `torch.cuda.empty_cache()` + `ipc_collect()`. Call after heavy operations. |

### Configuration & State
| Attribute | Type | Description |
| :--- | :--- | :--- |
| `app.app_config` | `dict` | Live user configuration. Persist changes with `app.save_app_config()`. |
| `app.voice_configs` | `dict` | Loaded clone voice profiles (name → `{audio_path, transcript}`). |
| `app.design_profiles` | `dict` | Custom Voice Design profiles (name → `{desc, instruct, temp, top_p}`). |
| `app.voice_recipes` | `dict` | Built-in read-only Voice Design recipes. |
| `app.set_busy(state, msg)` | method | Lock/unlock the UI and update the status message. |

### Batch Studio
| Attribute | Type | Description |
| :--- | :--- | :--- |
| `app.director` | `BatchDirector` | The Batch Studio controller. Access blocks via `app.director.blocks`. |

### Generation Controls
| Attribute | Type | Description |
| :--- | :--- | :--- |
| `app.speaker_var` | `tk.StringVar` | Current speaker selection in Custom Voice tab. |
| `app.seed_var` | `tk.StringVar` | Seed field in Precision Settings. |
| `app.start_gen_custom()` | method | Trigger Custom Voice generation. |

---

## 🔄 Generation Callbacks

The `switch_model` method accepts an optional callback fired after the model finishes loading:

```python
def on_engine_ready():
    print(f"Engine is ready: {app.current_model_type}")

app.switch_model("custom", on_success=on_engine_ready)
```

---

## 📋 Monkey-Patching for Seamless Integration

For plugins that need to intercept existing behaviour (e.g., filtering the style dropdown), you can replace methods on the app instance:

```python
def initialize(app):
    original_update = app.update_style_combo

    def filtered_update():
        original_update()
        # Post-process the combo values
        current = list(app.style_combo["values"])
        app.style_combo["values"] = [v for v in current if not v.startswith("_")]

    app.update_style_combo = filtered_update
```

The Style & Profile Manager (`style_profile_manager_plugin.py`) uses this pattern to filter disabled styles and profiles from all dropdowns.

---

© 2026 Blues Creative Engineering.
