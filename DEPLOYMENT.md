# 🚀 Professional Deployment Protocol (Smart Hybrid)
**Status:** ACTIVE | **Method:** Stub Installer + Hugging Face Cloud + Smart Patching
**Version:** 4.0.0 (Production)

## 1. The Architecture
We utilize a **Hybrid Deployment** strategy to bypass GitHub's file size limits and maintain a version-aware local environment.

1.  **The "Launcher" (The Hub):** A lightweight executable (`app_launcher.py`) that checks GitHub for a `version.json` manifest.
2.  **The "Brain" (The Engine):** A massive (~4.5GB) archive hosted on **Hugging Face**.
3.  **The "Smart Patch":** Small code updates (UI, logic fixes) are delivered as tiny ZIP files, allowing the launcher to update the app without re-downloading the engine.

---

## 2. Hosting & Manifest Setup

### Hugging Face (Heavy Assets)
1.  **Zip the Engine:** Compress your local `Qwen3-TTS` folder.
2.  **Upload:** Use the `resolve` link format for direct downloads.

### GitHub (Manifest & Patches)
1.  **version.json**: This file on GitHub acts as the source of truth.
    ```json
    {
      "current_version": "4.0.0",
      "min_launcher_version": "1.1.0",
      "patch_url": "link_to_small_zip",
      "full_url": "link_to_heavy_engine"
    }
    ```
2.  **version.txt**: A local file in the app directory that stores the currently installed version string.

---

## 3. The Release Cycle

### To push a small Code Patch:
1.  Zip only the changed `.py` files and new plugins.
2.  Upload to Hugging Face or GitHub.
3.  Update `version.json` on GitHub. Users' launchers will auto-apply the patch on next boot.

### To push a major Engine Update:
1.  Upload the full engine ZIP.
2.  Update the `current_version` in `version.json` (incrementing the major number, e.g., 3.x to 4.x).
3.  The launcher will prompt the user for a full download.

---

## 4. The Build Process
To release a new standalone Launcher:

1.  **Run Builder:**
    ```powershell
    python build_tiny.py
    ```
2.  **Verify Output:** Ensure the resulting EXE is small (~15-20MB).

---

## 5. Troubleshooting
* **"Update Loop":** Ensure `version.txt` is updated ONLY after a successful ZIP extraction.
* **"Permission Denied":** The app must have write access to its own folder to apply patches.
* **"Offline Boot":** If the GitHub manifest is unreachable, the launcher defaults to the existing local version.