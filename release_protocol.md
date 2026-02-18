Based on the file you just uploaded, **no, it is NOT updated.**

The current version in your file still describes the "Old Way" (building `installer.py` inside your main project folder). If you or a future Gemini follows that, you will get the **3GB Installer Bug** again.

I have rewritten the **Master Protocol** below. It now explicitly includes:

1. **The "Clean Room" Strategy:** Building in `C:\Users\1very\source\installer_dist`.
2. **The `venv_lite`:** Using the separate, tiny Python environment.
3. **The Three-URL Config:** Reminding you to update App, Engine, *and* Patch URLs.

Save this as **`RELEASE_PROTOCOL.md`**.

---

# 🚀 QWEN3 STUDIO: RELEASE PROTOCOL (GOD MODE)

**Author:** Blues | **Location:** Sitges HQ
**Objective:** Fail-safe protocol to build, package, and deploy Qwen3 Studio.

---

## 🛑 PHASE 1: PREP & VERSIONING

*Before you cook, check the prep.*

1. **Update Configuration**
* Open `release_config.json`.
* Change `"app_version": "4.0"` to your new version (e.g., `"4.1"`).
* *Note:* This automatically updates the zip filename (e.g., `Qwen3Studio_v4.1.zip`).


2. **Code Safety Check (The "Shutil" Rule)**
* Ensure the following files have `import shutil` at the top.
* `app_launcher.py` (Critical)
* `install_tutorials.py` (Critical)
* `installer.py` (Critical)





---

## 🍳 PHASE 2: THE APP BUILD (The Heavy Engine)

*Compiling the main application into a folder (OneDir).*

1. **Environment:** Use your **Main Project Venv** (`.venv`).
2. **Clean & Build:**
```bash
pyinstaller Qwen3Studio.spec --clean --noconfirm

```


3. **Sanity Test:**
* Run `dist/Qwen3Studio/Qwen3Studio.exe`.
* Ensure it opens without crashing.



---

## ☁️ PHASE 3: THE PAYLOAD (Hugging Face)

*Shipping the 4GB+ payload to the cloud.*

1. **Run the Auto-Uploader:**
```bash
python upload_to_hf.py app

```


2. **Get the Link:**
* Go to [Hugging Face Repo]().
* Copy the **Download Link** for the new zip (e.g., `Qwen3Studio_v4.1.zip`).



---

## 📦 PHASE 4: THE INSTALLER (The "Clean Room" Build)

*Building the lightweight (~15MB) setup file. WE DO NOT BUILD THIS IN THE MAIN FOLDER.*

**Location:** `C:\Users\1very\source\installer_dist`

1. **Update `installer.py` URLs**
* Open `installer.py` in your editor.
* Update **APP_ZIP_URL** (from Phase 3).
* Update **ENGINE_ZIP_URL** (The 11GB Engine link).
* Update **PATCH_ZIP_URL** (The `qwen_tts.zip` Logic Patch).


2. **Move Files to Clean Room**
* Copy `installer.py` and `pq.ico` -> `C:\Users\1very\source\installer_dist`.


3. **Activate "Lite" Environment**
* Open Terminal.
* Navigate: `cd C:\Users\1very\source\installer_dist`
* Activate:
```powershell
.\venv_lite\Scripts\activate

```


* *Check:* Prompt should say `(venv_lite)`.


4. **Build the Installer (Strict Single File)**
```powershell
pyinstaller --noconfirm --onefile --console --uac-admin --name "Qwen3_Setup_v4.1" --add-data "pq.ico;." --icon "pq.ico" installer.py

```


5. **Verify Size**
* Check `dist/Qwen3_Setup_v4.1.exe`.
* **Target:** ~15MB.
* *Fail:* If >100MB, you are using the wrong venv!



---

## 🚀 PHASE 5: DEPLOYMENT (GitHub)

*Opening the doors.*

1. **Final Test**
* Run the new Installer from your Desktop.
* Verify it installs App + Engine + Patch.
* Verify the App launches and loads the model.


2. **Push to GitHub**
* Create Release `v4.1`.
* Upload **ONLY** `Qwen3_Setup_v4.1.exe`.



---

### 🤖 Can Gemini do this?

**Yes.** If you feed this file to a future Gemini session, it will understand:

1. It cannot use the standard environment for the installer.
2. It must ask you to switch folders.
3. It must check for the 3 URLs.