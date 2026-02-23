# 🎙️ Qwen3-TTS Pro Suite v4.6.0

**Local AI Voice Design, Cloning, and Batch Production**

Qwen3-TTS Pro Suite is a professional-grade "Director" for speech synthesis. Built on the powerful Qwen2.5-Audio architecture, it provides a comprehensive local workflow for creating, managing, and rendering high-quality AI voices without any cloud dependencies or subscription fees.

---

## ⚠️ Safety & GPU Disclaimer

**IMPORTANT: READ BEFORE RUNNING**
This application uses high-performance AI models that heavily utilize your GPU.
* **Thermal Monitoring**: Ensure your system has adequate cooling. Monitor GPU temperatures during long batch runs.
* **Responsibility**: By using this software, you acknowledge that you are running it at your own risk. **Blues Creative Engineering** is not responsible for any hardware damage, data loss, or system instability.
* **Power Supply**: High-end AI inference can cause significant power spikes. Ensure your PSU is rated for your GPU's peak performance.

## 🛡️ Windows Smart App Control

Because this is an unsigned, open-source project, Windows 11 **Smart App Control** or **Windows Defender** may flag the application.
To run the suite:
1. If blocked, click "More Info" and "Run Anyway".
2. Ensure you have enough disk space (approx 15GB) for the local engines.
3. The app does not require internet after the initial engine download.

---

## 🚀 Key Features

* **Three Creative Engines**:
    * 🟢 **Custom Voice**: Command high-quality pre-trained personas (Ryan, Vivian, Sohee, etc.) with natural language style instructions.
    * 🔵 **Voice Design**: Create entirely new vocal identities from scratch using text descriptions.
    * 🟣 **Voice Clone**: Perfect digital replicas of any voice from just a few seconds of reference audio.
* **Batch Studio (Non-Linear Editor)**: A full production pipeline for multi-voice scripts. Per-block single generation (⚡ Gen), Multi-Take picker (🎲 x3), deterministic Seed control, and a colour-coded review/approval workflow.
* **Deterministic Generation (Seed)**: Pin any integer seed before generating to get a perfectly reproducible take every time. Accepted Multi-Takes write their seed back automatically.
* **Style & Profile Manager**: Inline enable/disable and editing of all custom Styles and Voice Design Profiles from a single panel.
* **Aggressive VRAM Management**: `flush_vram()` utility called between every block and take, plus a meta-tensor safety guard that severs corrupted model references before they crash the batch.
* **Modules Manager**: Unified tab to synchronise plugins with the official GitHub repository and toggle features on/off dynamically without restarting.
* **Smart Patch Update System**: The launcher detects and applies small patches automatically, keeping your installation current without re-downloading the heavy engine.
* **Persistent Settings**: User settings and module states are stored in `%LOCALAPPDATA%\Qwen3Studio\` and survive updates.
* **VRAM Monitor**: Real-time GPU memory tracking in the status bar.
* **Prep Station**: Built-in **Whisper AI** transcription for reference file preparation.

---

## 📦 Getting Started

### 1. Requirements
* **OS**: Windows 10/11 (win32)
* **GPU**: NVIDIA RTX (8GB+ VRAM recommended)
* **Python**: 3.10+

### 2. Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/1verysimple-lab/Qwen3-TTS.git
   cd Qwen3-TTS
   ```
2. **For NVIDIA GPU users:** Install PyTorch with the correct CUDA build first to avoid "kernel image" errors:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```
3. Install remaining dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Launch
Always start via the **Smart Launcher**:
```bash
python app_launcher.py
```

---

## 🔧 System Configuration

* **SoX Folder**: Place SoX binaries in `./sox/`.
* **AI Engines**: Models are automatically placed in `%LOCALAPPDATA%\Qwen3Studio\Qwen3-TTS\`.
* **MP3 Support**: Drop `libmp3lame-0.dll` directly into `./sox/` to enable MP3 export.

---

## 📖 Documentation

* **[Features & Specs](FEATURES.md)**: Detailed breakdown of capabilities and engines.
* **[Developer SDK / Plugin Guide](PLUGINS.md)**: How to build extensions.
* **[User Guide & Style Tips](GUIDE.md)**: Best practices and style reference.
* **[Release Protocol](release_protocol.md)**: Build and deployment instructions.

---

## 🎓 Official Documentation & Community

* **Project Page**: [https://blues-lab.pro](https://blues-lab.pro)
* **Built by**: [Blues Creative Engineering](https://blues-lab.pro)

---

## ⚖️ License

This project is licensed under the Apache-2.0 License. AI models are subject to the original Qwen license terms.

---

## 📁 Project Structure

### 🏗️ Core Application
| File | Description |
| :--- | :--- |
| **`app_main.py`** | Main GUI application — `QwenTTSApp` class, all tabs, engine wiring, and `ModuleHub`. |
| **`app_launcher.py`** | Smart launcher: integrity checks, auto-patch, engine download. |
| **`batch_director.py`** | Batch Studio — `BatchDirector` and `ScriptBlock` with Multi-Take, Seed, and per-block generation. |
| **`config_manager.py`** | HuggingFace hub integration, model repo resolution, system checks. |
| **`modules/`** | Dynamic plugin directory. Drop `.py` files here to extend the app. |
| **`qwen_tts/`** | AI model inference package (`core/`, `cli/`, `inference/`). |

### 🛠️ Build & Release
| File | Description |
| :--- | :--- |
| **`bump_version.py`** | Updates version numbers across all relevant files in one command. |
| **`deploy_workflow.py`** | Interactive guided deployment: build → upload → release. |
| **`installer.py`** | Standalone installer builder (run from clean-room environment). |
| **`release_config.json`** | Version metadata and HuggingFace repo IDs. |
| **`requirements.txt`** | Python dependencies for running from source. |

### 📄 Documentation & Assets
| File | Description |
| :--- | :--- |
| **`README.md`** | This file. Project overview and quick-start. |
| **`GUIDE.md`** | Style reference, tone recipes, and directionsl tips. |
| **`FEATURES.md`** | Full functional specification. |
| **`PLUGINS.md`** | Plugin SDK and developer guide. |
| **`CLAUDE.md`** | AI coding assistant context file. |
| **`tutorials/`** | JSON scripts for the interactive tutorial system. |
| **`pq.ico`** | Application icon. |

*Built with ❤️ by Blues in Spain.*
