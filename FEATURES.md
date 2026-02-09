# 🎙️ Qwen3-TTS Pro Suite: Functional Specification (v3.9.0)

This document outlines the full functional capabilities of the **Qwen3-TTS Pro Suite**, organized by the logical creative workflow.

---

## 1. Core Architectural Pillars

### 🧱 Stability & Flexibility
The application balances local stability with power-user flexibility:
*   **Audio Processor**: Forced to root `./sox/` folder for binary reliability.
*   **Custom Engine Root**: Users can select a custom folder for the large AI models (15GB+) via the Launcher or Settings to save space on their primary drive.
*   **Smart Downloader**: Integrated HuggingFace hub downloader fetches missing assets on-demand.
*   **VRAM Monitor**: Real-time monitoring of GPU memory usage with color-coded safety indicators.

### 🔌 Module Hub (Extension System)
The "Triple Pavilion" architecture for module management:
*   **GitHub Synchronization**: A surgical sync engine via GitHub REST API to pull the latest official plugins without full git overhead.
*   **Registry Management**: A persistence layer (`enabled_modules.json`) to toggle modules on/off.
*   **Dynamic Plugin Architecture**: Supports both UI-based tabs and Headless background services.
*   **Blues-Approved Headers**: Security check to verify plugin validity before initialization.

---

## 2. Creative Engines

### 🟢 Custom Voice (Instructional)
Command existing high-quality personas using natural language.
*   **Style Injection**: "Speak softly", "Sound excited", "Whispering", etc.
*   **Persona Selection**: Access to pre-trained high-fidelity speakers (Ryan, Aiden, Vivian, Serena, Eric, etc.).
*   **Prompting**: Dynamic style and instruction fields for nuanced performance.

### 🔵 Voice Design (Generative)
Create unique voices that have never existed.
*   **Description Driven**: "A gravelly old wizard with a British accent."
*   **Seed Generation**: Generates a completely new vocal fingerprint based on your text.
*   **Clone Source**: Designed voices can be used as sources for the Cloning engine for high stability.

### 🟣 Voice Clone (Replica)
Perfect digital mimicry of a specific individual.
*   **Rapid Cloning**: Requires only 3-10 seconds of reference audio.
*   **Locked Voice**: Cache speaker profiles to generate thousands of lines without re-processing the reference.
*   **Segment Rendering**: Support for multi-sentence processing using the `||` delimiter for long-form content.

---

## 3. Production Workflows

### 🎬 Batch Studio (Director)
The Non-Linear Editor for audio production.
*   **Script Blocks**: Sequence lines from different engines in a single timeline.
*   **Multi-Engine Rendering**: Seamlessly switches between Custom, Design, and Clone models during a batch run.
*   **Draft Preview**: Real-time management of individual blocks before final export.

### 📝 Transcript Helper (Prep Station)
Powered by **Faster-Whisper**.
*   **Audio-to-Text**: Automatically transcribe reference files for cloning.
*   **Profile Integration**: Save transcriptions directly into speaker profiles.

---

## 4. System & Integration

### 🚀 Smart Launcher
*   **Integrity Check**: Verifies SoX and Model presence before booting.
*   **Error Recovery**: Catches common initialization failures and provides user-friendly guidance.

### ⚙️ System Status
*   **Real-time Monitoring**: Visual indicators for engine state (Idle, Busy, Error).
*   **MP3 Auto-Detect**: Unlocks MP3 export functionality immediately when `libmp3lame-0.dll` is detected in the `./sox/` folder.

---
© 2026 Blues Creative Engineering.
