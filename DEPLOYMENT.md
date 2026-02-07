# í ½íº€ Professional Deployment Protocol (Smart Hybrid)
**Status:** ACTIVE | **Method:** Stub Installer + Hugging Face Cloud
**Version:** 1.0 (Production)

## 1. The Architecture
We utilize a **Hybrid Deployment** strategy to bypass GitHub's file size limits and Google Drive's bandwidth quotas.

1.  **The "Stub" (The Installer):** A lightweight (~200MB) executable (`Qwen3_Studio_Setup.exe`). This contains the App Logic, UI, and Icons.
2.  **The "Brain" (The Engine):** A massive (~4.5GB) archive (`blues-Qwen3-TTS.zip`) hosted on **Hugging Face**.

**User Experience:**
1.  User downloads small EXE.
2.  User runs EXE.
3.  App detects missing engine in `%LOCALAPPDATA%`.
4.  App auto-downloads from Hugging Face (High Speed).
5.  App launches seamlessly.

---

## 2. Hosting the Engine (One-Time Setup)
*Current Host:* **Hugging Face** (Unlimited Bandwidth)

1.  **Zip the Engine:** Compress your local `Qwen3-TTS` folder into `blues-Qwen3-TTS.zip`.
2.  **Upload:** Upload to a public Hugging Face Model repository.
3.  **Get Link:** Copy the download link.
    * **CRITICAL:** Must use the `resolve` link format:
    * `https://huggingface.co/USERNAME/MODEL/resolve/main/FILE.zip?download=true`

---

## 3. The Code Configuration
Ensure `app_launcher.py` and `app_main.py` are synchronized to the **AppData** standard.

**A. app_launcher.py (The Installer)**
* **Target:** `os.environ['LOCALAPPDATA'] + "/Qwen3Studio"`
* **Source:** Your Hugging Face Link.
* **Logic:** Download -> Extract -> Delete Zip -> Launch.

**B. app_main.py (The App)**
* **Engine Root:** Must point to `os.path.join(os.environ['LOCALAPPDATA'], "Qwen3Studio", "Qwen3-TTS")`.
* **Instance Lock:** Must check `app.lock` in the Base Directory to prevent double-opening.

---

## 4. The Build Process (Release Cycle)
To release a new version of the App (Logic/UI) without forcing users to re-download the 4.5GB engine:

1.  **Clean Workspace:**
    * Delete `dist/`, `build/`, and `_internal/` folders.
    * **IMPORTANT:** Ensure your local `Qwen3-TTS` folder is renamed or moved so it is **NOT** included in the build.
2.  **Run Builder:**
    ```powershell
    python build_distribution.py
    ```
3.  **Verify Output:**
    * Go to `Output/`.
    * Check file size (Should be ~150-200MB).
    * **Rename:** `Qwen3_Studio_Setup_vX.X.exe`.
4.  **Publish:**
    * Upload the EXE to GitHub Releases.

---

## 5. Troubleshooting
* **"Quota Exceeded":** Ensure you are using Hugging Face, not Google Drive.
* **"Permission Denied":** Ensure the app is writing to `AppData`, NOT `Program Files`.
* **"App Not Found":** Ensure `app_launcher.py` imports `app_main` directly, rather than using `subprocess` to call a file that doesn't exist in the frozen EXE.