# 🎙️ Qwen3-TTS Pro Suite v3.9.1

**Local AI Voice Design, Cloning, and Batch Production**

Qwen3-TTS Pro Suite is a professional-grade "Director" for speech synthesis. Built on the powerful Qwen2.5-Audio architecture, it provides a comprehensive local workflow for creating, managing, and rendering high-quality AI voices without any cloud dependencies or subscription fees.

---

## ⚠️ Safety & GPU Disclaimer

**IMPORTANT: READ BEFORE RUNNING**
This application uses high-performance AI models that heavily utilize your GPU. 
*   **Thermal Monitoring**: Ensure your system has adequate cooling. Monitor your GPU temperatures during long batch runs.
*   **Responsibility**: By using this software, you acknowledge that you are running it at your own risk. **Blues Creative Engineering** is not responsible for any hardware damage, data loss, or system instability caused by the use of this local AI suite.
*   **Power Supply**: High-end AI inference can cause significant power spikes. Ensure your PSU is rated for your GPU's peak performance.

## 🛡️ Windows Smart App Control

Because this is an unsigned, open-source project, Windows 11 **Smart App Control** or **Windows Defender** may flag the application. 
To run the suite:
1.  If blocked, click "More Info" and "Run Anyway".
2.  Ensure you have enough disk space (approx 15GB) for the local engines.
3.  The app does not require internet after the initial engine download.

---

## 🚀 Key Features

*   **Three Creative Engines**:
    *   🟢 **Custom Voice**: Use natural language instructions and style descriptors to command high-quality pre-trained personas.
    *   🔵 **Voice Design**: Create entirely new vocal identities from scratch using text descriptions.
    *   🟣 **Voice Clone**: Perfect digital replicas of any person from just a few seconds of reference audio.
*   **🔌 Module Hub (New)**: A unified manager to synchronize plugins with the official GitHub repository and toggle features on/off dynamically.
*   **Smart Director Architecture**: Includes an integrated **Batch Studio** (Non-Linear Editor) for sequencing complex multi-voice scripts and scenes.
*   **VRAM Monitor**: Real-time GPU memory tracking integrated into the status bar for stability.
*   **Dynamic Extension Support**: A modular plugin system allows you to add new features and automated scripting via the `modules/` folder. [Read the Plugin Guide (PLUGINS.md)](PLUGINS.md).
*   **Stability First**: Forced local path architecture ensures core components (SoX, Engines) are always where they need to be.
*   **Auto-Managed Engines**: Missing models are detected and downloaded automatically from HuggingFace.
*   **Prep Station**: Built-in **Whisper AI** for transcribing reference files and preparing data.

---

## 📦 Getting Started

### 1. Requirements
*   **OS**: Windows 10/11 (win32)
*   **GPU**: NVIDIA RTX (8GB+ VRAM recommended for optimal performance)
*   **Python**: 3.10+

### 2. Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/1verysimple-lab/Qwen3-TTS.git
   cd Qwen3-TTS
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Launch
Always start the application via the **Smart Launcher** to ensure system integrity:
```bash
python Pro_Studio_Launcher.py
```

---

## 🔧 System Configuration

*   **SoX Folder**: Place the SoX binaries in the `./sox/` folder.
*   **AI Engines**: Models will be automatically placed in the `./engine/` folder.
*   **MP3 Support**: To enable MP3 export, download `libmp3lame-0.dll` and drop it directly into the `./sox/` folder.

---

## 📖 Documentation

*   **[Features & Specs](FEATURES.md)**: Detailed breakdown of the creative engines.
*   **[Developer SDK / Plugin Guide](PLUGINS.md)**: Learn how to build extensions.
*   **[User Guide & Style Tips](GUIDE.md)**: Best practices for getting the best voices.
*   **[Build & Deployment](DEPLOYMENT.md)**: Technical notes for standalone building.

---

## 🎓 Official Documentation & Community

*   **Project Page**: [https://blues-lab.pro](https://blues-lab.pro)
*   **App by Blues**: [Blues Creative Engineering](https://blues-lab.pro)

---

## ⚖️ License
This project is licensed under the Apache-2.0 License. AI models are subject to the original Qwen license terms.

## ������ Project Structure

### ������ Core Application
| File | Description |
| :--- | :--- |
| **`app_main.py`** | The main entry point for the Qwen3 Studio application (The "Pro" App). |
| **`app_launcher.py`** | Handles environment setup and launches the main app. |
| **`config_manager.py`** | Manages user settings and configuration (paths, defaults). |
| **`batch_director.py`** | Logic for the "Podcast Mode" and batch processing. |
| **`modules/`** | Contains core logic for TTS, Voice Cloning, and Audio Processing. |
| **`qwen_tts/`** | Interface for the AI Model inference. |

### ������️ Installer & Build System
| File | Description |
| :--- | :--- |
| **`tiny_loader.py`** | Source code for the **Web Launcher**. Downloads the main app from Hugging Face. |
| **`build_tiny.py`** | Script to compile `tiny_loader.py` into the ~15MB `Qwen3_Launcher.exe`. |
| **`build_distribution.py`** | Script to build the full "Heavy" Pro App (2.7GB). |
| **`deploy_payload.py`** | Utility to zip and upload the Pro App to Hugging Face. |
| **`requirements.txt`** | Python dependencies required to run the source code. |

### ������ Documentation & Assets
| File | Description |
| :--- | :--- |
| **`README.md`** | Main project overview and user instructions. |
| **`GUIDE.md`** | Detailed user manual for Studio features. |
| **`FEATURES.md`** | Marketing list of capabilities. |
| **`tutorials/`** | JSON scripts used for the in-app interactive tutorial system. |
| **`pq.ico`** | Application icon file. |

*Built with ❤️ by Blues in Spain.*
