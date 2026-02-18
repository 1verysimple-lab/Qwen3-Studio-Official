# Application Architecture Summary

This document provides a summary of the application's architecture, including the location of the 'engine' and 'large file' components.

## Application Architecture

The application appears to be a Python-based desktop application with a focus on audio processing, specifically Text-to-Speech (TTS).

*   **Main Application:** The main application logic seems to be contained within `app_main.py` and launched by `app_launcher.py`.
*   **Dependencies:** The project's dependencies are managed in `requirements.txt`. Key libraries include `torch`, `torchaudio`, `transformers`, `faster-whisper`, and `gradio`, which suggests a deep learning-based audio application with a web-based UI.
*   **Modular Design:** The `modules` directory indicates a modular architecture, with different functionalities encapsulated in plugins.

## Engine

The core "engine" of the application is likely located in the `qwen_tts` directory. This directory contains the model, tokenizer, and inference logic for the Qwen3 TTS model, which is a powerful Text-to-Speech engine. The `faster-whisper` dependency also suggests that audio transcription might be another core "engine" component.

*   **TTS Engine:** `qwen_tts/`
*   **Transcription Engine (likely):** The code that uses the `faster-whisper` library.

## Large Files

The project contains several large files, primarily related to audio assets and binaries.

*   **Binaries:** The `sox/` directory contains the SoX audio utility, which is a collection of binary files.
*   **Audio Assets:**
    *   `docs/audio/`: Contains `.mp3` files, likely for promotional purposes.
    *   `saved_assets/`: Contains `.wav` files, which are likely user-saved audio files.
    *   `temp_outputs/`: Contains `.wav` files, which are temporary audio outputs from the application.
*   **Backup:** The `BACKUP PERFECT ONLY MISSING TO INSTALL.rar` file is a large archive.
*   **Virtual Environment:** The `.venv/` directory is also very large, but it is a local development environment and not part of the distributable application.
