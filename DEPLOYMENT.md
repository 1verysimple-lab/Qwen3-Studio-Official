# 📦 The Master Release Reference (v3.8.1)

## 🚀 The "Slim" Distribution Strategy
We distribute a lightweight installer that downloads the large AI models on the user's first run. This keeps the initial download small (~200MB) instead of 15GB.

### 1. Build the Application (.exe)
Run this command from your terminal to create the single-file launcher:

```bash
pyinstaller --noconsole --onefile --name="Qwen3_Studio_Pro" ^
--icon="pq.ico" ^
--add-data "tutorials;tutorials" ^
--add-data "sox;sox" ^
--add-data "modules;modules" ^
--add-data "pq.ico;." ^
--add-data "version.json;." ^
--hidden-import="scipy.special.cython_special" ^
"Pro_Studio_Launcher.py"
```

### 2. Create the Distribution Zip
Your final public archive should contain **ONLY** these items:
1.  `Qwen3_Studio_Pro.exe` (Found in `./dist/`)
2.  `sox/` folder (The folder containing `sox.exe` and binaries)

**Do NOT include:**
*   `engine/` folder (The app will download this)
*   `_internal/` or `build/` folders
*   `temp_outputs/`

---

## 🌍 Preparing for Public Release

### 1. Versioning & Identity
*   **Version**: Ensure `version.json` is set to `3.8.0`.
*   **Branding**: All headers reference "Blues Creative Engineering".
*   **Official Link**: [https://blues-lab.pro](https://blues-lab.pro)

### 2. The Setup Wizard Workflow
On first run, the user experience is:
1.  **Safety First**: A full-screen warning about **Windows Smart App Control** and how to bypass it.
2.  **Download Center**: One-click download for the 15GB AI engines via HuggingFace.
3.  **Finish**: Explaining that the very first launch will take 1-2 minutes to load into VRAM.

### 3. MP3 Support Strategy
Since we cannot redistribute the MP3 DLL directly:
1.  User clicks the Gear icon (⚙).
2.  The user follows the built-in guide to drop `libmp3lame-0.dll` into `./sox/`.
3.  Status flips to "✅ ACTIVE".

### 4. Repository Cleanup
Before pushing code, ensure you delete:
*   `*.log` files
*   `*.lock` files
*   `__pycache__`
*   Any previous `.zip` backups

---
© 2026 Blues Creative Engineering.