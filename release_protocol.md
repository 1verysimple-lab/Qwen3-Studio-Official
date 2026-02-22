# 🚀 QWEN3 STUDIO: RELEASE PROTOCOL

**Author:** Blues | **Location:** Sitges HQ
**Current Version:** 4.6.0
**Objective:** Fail-safe protocol to build, package, and deploy Qwen3 Studio.

---

## 🛑 PHASE 1: PREP & VERSIONING

*Before you cook, check the prep.*

1. **Bump the Version (Automated)**
   Use the version bump script to update all files in one go:
   ```bash
   python -X utf8 bump_version.py 4.X.0
   ```
   This updates `release_config.json`, `app_main.py`, `app_launcher.py`, `installer.py`, `deploy_workflow.py`, `README.md`, and `FEATURES.md` simultaneously.
   > ⚠️ Use `-X utf8` flag on Windows to prevent cp1252 encoding errors from arrow characters in print statements.

2. **Verify `release_config.json`**
   ```json
   {
     "app_name": "Qwen3Studio",
     "app_version": "4.X.0",
     "hf_repo_id": "Bluesed/QWEN_STUDIO",
     "engine_repo_id": "Bluesed/blues-qwen",
     "app_bundle_name": "Qwen3Studio_v4.X.0.zip",
     "engine_bundle_name": "blues-Qwen3-TTS.zip"
   }
   ```
   > ⚠️ Double-check that `app_bundle_name` has the `.` before `zip` — the bump script regex can eat it.

3. **Code Safety Check**
   Ensure the following files have `import shutil` at the top:
   - `app_launcher.py` (Critical)
   - `installer.py` (Critical)

---

## 🍳 PHASE 2: THE APP BUILD (The Heavy Package)

*Compiling the main application into a folder (OneDir).*

1. **Environment:** Use your **Main Project Venv** (`.venv`).
2. **Clean & Build:**
   ```bash
   pyinstaller Qwen3Studio.spec --clean --noconfirm
   ```
3. **Sanity Test:**
   - Run `dist/Qwen3Studio/Qwen3Studio.exe`.
   - Confirm it opens without crashing and that the engine loads.

---

## ☁️ PHASE 3: THE PAYLOAD (Hugging Face)

*Shipping the 4GB+ payload to the cloud.*

1. **Run the Auto-Uploader:**
   ```bash
   python upload_to_hf.py app
   ```
2. **Get the Link:**
   - Go to the [Hugging Face Repo](https://huggingface.co/Bluesed/QWEN_STUDIO).
   - Copy the **Download Link** for the new zip (e.g., `Qwen3Studio_v4.X.0.zip`).

---

## 📦 PHASE 4: THE INSTALLER (The "Clean Room" Build)

*Building the lightweight (~15MB) setup file.*

**⚠️ DO NOT build the installer inside the main project folder** — it will bundle the entire venv and produce a 3GB+ binary.

**Location:** `C:\Users\1very\source\installer_dist`

1. **Update `installer.py` URLs**
   Open `installer.py` and update:
   - `APP_ZIP_URL` — from Phase 3.
   - `ENGINE_ZIP_URL` — the 11GB engine link.
   - `PATCH_ZIP_URL` — the `qwen_tts.zip` logic patch.

2. **Move Files to Clean Room**
   ```powershell
   copy installer.py C:\Users\1very\source\installer_dist\
   copy pq.ico C:\Users\1very\source\installer_dist\
   ```

3. **Activate the Lite Environment**
   ```powershell
   cd C:\Users\1very\source\installer_dist
   .\venv_lite\Scripts\activate
   ```
   Prompt should show `(venv_lite)`.

4. **Build the Installer (Strict Single File)**
   ```powershell
   pyinstaller --noconfirm --onefile --console --uac-admin --name "Qwen3_Setup_v4.X.0" --add-data "pq.ico;." --icon "pq.ico" installer.py
   ```

5. **Verify Size**
   - Check `dist/Qwen3_Setup_v4.X.0.exe`.
   - **Target:** ~15MB.
   - **Fail condition:** If >100MB, you are using the wrong venv.

---

## 🚀 PHASE 5: DEPLOYMENT (GitHub)

*Opening the doors.*

1. **Final Test**
   - Run the new installer from a clean location (Desktop).
   - Verify it installs App + Engine + Patch.
   - Verify the app launches and the model loads.

2. **Push to GitHub**
   - Create Release `v4.X.0`.
   - Upload **only** `Qwen3_Setup_v4.X.0.exe`.
   - Paste the release notes from `FEATURES.md`.

3. **Update Website** (if applicable)
   - Update download link on [blues-lab.pro](https://blues-lab.pro).

---

## 🤖 For Future AI Sessions

If you feed this file to a future AI session, it will understand:
1. The installer must be built from `C:\Users\1very\source\installer_dist` using `venv_lite`.
2. The bump script requires `-X utf8` on Windows.
3. Three URLs must be updated in `installer.py` before building.
4. Check `app_bundle_name` in `release_config.json` for the missing-dot bug after bumping.
