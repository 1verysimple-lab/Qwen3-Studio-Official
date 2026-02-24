# 🎙️ Qwen3-TTS Pro Suite: Functional Specification (v4.6.1)

This document outlines the full functional capabilities of the **Qwen3-TTS Pro Suite**, organised by logical workflow.

---

## 1. Core Architecture

### 🧱 Stability & Reliability
* **Forced Local Paths**: SoX binaries are always loaded from `./sox/` — never from system PATH — for binary reliability.
* **Custom Engine Root**: The Launcher and Settings panel allow redirecting the 15GB+ model files to any drive.
* **Smart Downloader**: Integrated HuggingFace hub downloader fetches missing assets on first run.
* **VRAM Monitor**: Real-time GPU memory usage display with colour-coded safety indicators in the status bar.
* **VRAM Flush Utility**: `flush_vram()` — calls `gc.collect()`, `torch.cuda.empty_cache()`, and `torch.cuda.ipc_collect()` — is invoked between every block generation and every multi-take iteration to prevent accumulation.
* **Meta-Tensor Safety Guard**: Before every batch run and every multi-take, the worker inspects model parameters. If a weight is found on the `"meta"` device (VRAM overflow indicator), it immediately severs the model reference, flushes VRAM, and surfaces a clear error rather than allowing the batch to silently corrupt.
* **Smart Patch Update System**: Version-aware launcher handles small code patches and full engine migrations seamlessly.
* **Persistent Settings**: All user settings and module states stored in `%LOCALAPPDATA%\Qwen3Studio\` survive application updates.

### 🔌 Modules Manager (Extension System)
* **GitHub Synchronisation**: Surgical sync via GitHub REST API pulls the latest official plugins without full git overhead.
* **Registry Management**: `enabled_modules.json` toggle — enable or disable any plugin instantly without restarting.
* **Dynamic Plugin Architecture**: Supports UI-tab plugins and headless background services.
* **Blues-Approved Headers**: Security header check verifies plugin authenticity before initialisation.
* **Bundled Plugins**: Tutorial, Peak Meter, Style & Profile Manager. Autoscript provided as a disabled demo.

---

## 2. Creative Engines

### 🟢 Custom Voice (Instructional)
Command existing high-quality pre-trained personas using natural language.
* **Style Injection**: "Speak softly", "Sound excited", "Whispering", etc.
* **Persona Selection**: Ryan, Aiden, Vivian, Serena, Eric, Dylan, Uncle_Fu, Ono_Anna, Sohee.
* **Instruction Field**: Dynamic style direction for nuanced per-generation performance.

### 🔵 Voice Design (Generative)
Create unique voices that have never existed.
* **Description-Driven**: "A gravelly old wizard with a British accent."
* **Seed Control**: Provide a seed to reproduce an exact vocal fingerprint, or leave blank for a fresh random identity.
* **Clone Source**: Designed voices can be exported and used as sources for the Clone engine for high consistency.

### 🟣 Voice Clone (Replica)
Precise mimicry of a specific individual.
* **Rapid Cloning**: Requires only 3–10 seconds of reference audio.
* **Prompt Caching**: Speaker voice prompt is built once per batch speaker, not per block — eliminates redundant processing on multi-block clone runs.
* **Segment Rendering**: Multi-sentence processing via the `||` delimiter for long-form content.

---

## 3. Production Workflows

### Batch Studio (Non-Linear Editor)
The full production pipeline for multi-voice audio scenes.

* **Script Blocks**: Each block holds one line of dialogue with its own Speaker, Style, Language, Seed, Temperature, and Top P.
* **Status System**: Blocks cycle through Grey (pending) → Blue (busy) → Yellow (review) → Green (accepted) → Red (rejected). The Run button skips accepted (green) blocks, re-generating only pending and rejected ones.
* **⚡ Per-Block Generation**: The ⚡ Gen button generates only that single block without disturbing the rest of the scene. `play_on_complete` is suppressed so it doesn't trigger Play All.
* **🎲 Multi-Take (x3)**: Generates three independent variations of a block in the background (each with a fresh random seed), then presents a modal picker dialog with Play and Accept buttons per take. Accepting a take writes the winning audio, sample rate, and seed back into the block automatically.
* **Seed Control**: An integer in the Seed field pins the random state for a deterministic, reproducible result. Leaving it empty selects a random seed at generation time and writes it back so the take can always be reproduced.
* **⚡ Auto-Switch**: When enabled, the director automatically switches engines between blocks as required — no manual intervention needed.
* **🔍 Auto-Verify Batch**: When enabled, runs a two-pass quality audit on every block immediately after scene generation completes. Silently unloads the speech engine, loads Faster-Whisper, and checks each block for (1) unnatural silences longer than 2 seconds (RMS dropout scan) and (2) transcription accuracy against the original script (fuzzy match ≥ 75%). Blocks that fail either check are flagged yellow with a hover tooltip stating the specific failure reason. After the audit, Faster-Whisper is unloaded and the speech engine is reloaded automatically so the studio is immediately ready for the next run. Requires `faster-whisper` (`pip install faster-whisper`).
* **Clone Prompt Caching**: Within a batch run, the voice clone prompt for a given speaker is computed once and cached for reuse across consecutive blocks with the same speaker.
* **Save / Load**: Entire scenes (blocks, audio, seeds, status) serialised to JSON for resuming later.
* **Collapsible Blocks**: Each block can be collapsed to a compact header to keep long scripts manageable.

### Transcript Helper (Prep Station)
Powered by **Faster-Whisper**.
* **Audio-to-Text**: Automatically transcribe reference files to prepare them for the Clone engine.
* **Profile Integration**: Save transcriptions directly into voice profiles.

---

## 4. Style & Profile Manager Plugin

A dedicated panel (🗂 Manager tab) for managing the growing library of styles and profiles.
* **Styles Panel**: View, enable/disable, create, and inline-edit all custom style instructions. Built-in styles are protected from deletion but can be disabled.
* **Profiles Panel**: View, enable/disable, create, and inline-edit Voice Design profiles (name, description, instruction, Temperature, Top P sliders). Built-in recipes are read-only.
* **Live Patching**: Changes sync immediately — the Style and Speaker dropdowns in the main UI and Batch Studio update without restarting.

---

## 5. System & Integration

### Smart Launcher
* **Integrity Check**: Verifies SoX and model presence before booting the UI.
* **Automatic Patching**: Detects new versions on GitHub and applies code patches on launch.
* **Error Recovery**: Catches common initialisation failures and provides user-friendly guidance.

### System Status Header
* **Real-time Engine Indicator**: Visual status icon shows Idle / Busy / Error state with colour coding.
* **Active Model Label**: Shows which engine (Custom / Design / Clone) is currently loaded.
* **STOP Button**: Cancels any in-progress generation immediately.
* **🔄 Reset Button**: Emergency abort + model reload for situations where generation hangs or a VRAM crash occurs.
* **MP3 Auto-Detect**: Unlocks MP3 export immediately when `libmp3lame-0.dll` is detected.

---

© 2026 Blues Creative Engineering.
