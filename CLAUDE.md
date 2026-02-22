# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Qwen3-TTS Pro Suite** — A Windows desktop AI voice generation application built with Tkinter. It wraps local Qwen3-TTS models (via HuggingFace) in a GUI with three synthesis engines: Custom Voice, Voice Design, and Voice Clone. The app targets NVIDIA GPUs (8GB+ VRAM) and runs entirely offline after initial model download.

## Running the App

```bash
python app_launcher.py        # Always use the launcher, not app_main.py directly
```

The launcher performs integrity checks, downloads missing engine models from HuggingFace, and applies patches before starting the UI.

**Installation from scratch:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
python app_launcher.py
```

**Requirements:** Windows 10/11, Python 3.10+, NVIDIA GPU with 8GB+ VRAM, SoX placed in `./sox/` folder.

## Build & Release

```bash
python bump_version.py              # Bump version number across files
python deploy_workflow.py           # Interactive guided deployment (build → upload → release)
python installer.py                 # Standalone installer builder
```

PyInstaller specs: `Qwen3Studio.spec` (main app), `Qwen3_Launcher.spec` (launcher binary).

## Architecture

### Entry Flow
```
app_launcher.py → (integrity check, patch, download) → app_main.py:launch_studio()
                                                              ↓
                                                        QwenTTSApp (Tkinter root)
                                                              ↓
                                              ModuleHub loads ./modules/ plugins
```

### Key Files
| File | Purpose |
|------|---------|
| `app_main.py` | Main GUI app — 4,100+ lines, contains `QwenTTSApp` class and `ModuleHub` |
| `app_launcher.py` | Smart launcher with engine download and auto-patch logic |
| `batch_director.py` | Batch Studio tab — `BatchDirector` and `ScriptBlock` classes |
| `config_manager.py` | HuggingFace hub integration and system checks |
| `app_config.json` | User settings (persisted voices, design profiles, style instructions) |
| `release_config.json` | Version metadata and HuggingFace repo IDs |
| `qwen_tts/` | AI model inference package (core/, cli/, inference/) |

### Path Layout (at Runtime)
- `BASE_DIR` — repo root (or `sys._MEIPASS` if frozen)
- `%LOCALAPPDATA%\Qwen3Studio\` — persistent app data
- `%LOCALAPPDATA%\Qwen3Studio\Qwen3-TTS\` — AI engine models
- `./sox/sox.exe` — SoX audio processor (must be local, not system PATH)
- `./app_config.json` — user config (lives in repo root)
- `./modules/` — plugin directory

### Three Synthesis Engines
- **Custom Voice (green tab):** Uses pre-trained personas (Ryan, Aiden, Vivian, etc.) + style instructions
- **Voice Design (blue tab):** Generates new vocal fingerprints from text descriptions
- **Voice Clone (purple tab):** Clones a voice from 3–10 seconds of reference audio

### Plugin System (`ModuleHub`)
Plugins live in `./modules/` and must export an `initialize(app)` function:
```python
def initialize(app):
    # app is the QwenTTSApp instance
    # app.notebook — add tabs
    # app.model — access inference engine
```
Registry stored at `%LOCALAPPDATA%\Qwen3Studio\enabled_modules.json`. Modules Manager tab supports GitHub sync to pull latest plugins from the official repo.

Active plugins: `text_parser_plugin.py`, `tutorial_plugin.py`, `peak_meter_plugin.py`, `style_profile_manager_plugin.py`.

### HuggingFace Repos
- App distribution: `Bluesed/QWEN_STUDIO`
- Engine models: `Bluesed/blues-qwen`
- Upstream models: `Qwen/Qwen3-TTS-12Hz-1.7B-{CustomVoice,Base,VoiceDesign}`

## Important Conventions
- `||` delimiter splits long text into segments in Voice Clone mode for consistent rendering
- Action tags in synthesis text: `<laughter>`, `<breath>`, `<sigh>` — see `GUIDE.md` for full list
- Version is tracked in `release_config.json` (`app_version` field) and must be bumped via `bump_version.py`
- Run `bump_version.py` with `python -X utf8 bump_version.py <version>` on Windows to avoid cp1252 encoding errors
- The app is unsigned; Windows Smart App Control warnings are expected on distribution

## Key Features Added in v4.6.0
- **Seed control**: `seed_var` (StringVar) in main UI and per-block in Batch Studio. Resolved to `int` before every generate call; written back if randomly chosen.
- **Multi-Take (🎲 x3)**: `BatchDirector.generate_multi_takes(block)` → `_multi_take_worker` → `_show_take_picker` modal. Generates 3 variations, lets user pick; winning seed written back.
- **Per-block generation**: `ScriptBlock.btn_generate` calls `generate_callback` → `BatchDirector.generate_single_block`; `play_on_complete=False` suppresses Play All.
- **`flush_vram()`**: `QwenTTSApp` method — `gc.collect()` + `torch.cuda.empty_cache()` + `ipc_collect()`. Called after every block and every multi-take iteration.
- **Meta-tensor guard**: Both `_generation_worker` and `_multi_take_worker` inspect model parameters. If device == `"meta"`, severs `app.model = None`, calls `flush_vram()`, raises descriptive `RuntimeError`.
- **Style & Profile Manager**: `modules/style_profile_manager_plugin.py` — monkey-patches `app.update_style_combo` and `app.director.get_styles` to filter disabled items. Uses `app_config["disabled_styles"]` and `app_config["disabled_profiles"]`.
- **Flat.TButton**: ttk style defined in `setup_styles()`. Used by all Batch Studio block buttons for a cleaner look.
- **Help system**: `_configure_help_tags()` and `_render_help_text()` module-level helpers parse `## ` sub-headers and `•` bullets into styled `tk.Text` tags in both `show_help_guide` and `show_context_help`.
