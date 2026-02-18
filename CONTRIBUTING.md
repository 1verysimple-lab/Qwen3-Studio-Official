# 🛠️ Contributing to Qwen3 Studio

First off, thank you for considering contributing to the project! We welcome any help you can offer.

## Development Environment Setup

If you want to work on the source code, you'll need to set up a local development environment.

### 1. Requirements
*   **OS**: Windows 10/11
*   **GPU**: NVIDIA RTX (8GB+ VRAM recommended for optimal performance)
*   **Python**: 3.10+
*   **Git**: [https://git-scm.com/](https://git-scm.com/)

### 2. Installation Steps
1.  Clone the official repository:
    ```bash
    git clone https://github.com/1verysimple-lab/Qwen3-Studio-Official.git
    cd Qwen3-Studio-Official
    ```
2.  Create and activate a Python virtual environment. This is highly recommended to avoid conflicts with other projects.
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```
3.  **For NVIDIA GPU users (especially RTX series):** To ensure optimal CUDA compatibility and prevent "kernel image" errors, it is highly recommended to manually install PyTorch with the universal NVIDIA build *before* running `pip install -r requirements.txt`.
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```
4.  Install the remaining project dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Launching from Source
Always start the application via the **Smart Launcher** to ensure all checks are performed:
```bash
python app_launcher.py
```

---

## 🚀 Build and Deployment

For a complete guide on how to build the application bundle and the final installer, please see the **[Build & Deployment Guide](BUILD_AND_DEPLOY.md)**.
