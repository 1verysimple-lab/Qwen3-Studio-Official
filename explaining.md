# 📂 Qwen3 Studio Pro: User Journey & Technical Operations

This document explains exactly what happens when a user interacts with the Qwen3 Studio Pro distribution package.

---

## 1. Extraction & First Run (The "Out of Box" Experience)

When a user extracts the ZIP and double-clicks `Qwen3_Studio_Pro.exe`, the following sequence occurs:

### Phase A: Instance Check & Environment Prep
*   The app checks for `launcher.lock`. If found, it stops (preventing duplicate processes).
*   It automatically adds the bundled `./sox/` folder to the system PATH for that session only.

### Phase B: The Setup Wizard (First Time Only)
If the AI models (15GB) are not detected in the `./engine` folder, the **Setup Wizard** triggers automatically:
1.  **Welcome:** Highlights the hardware requirements.
2.  **Security:** Educates the user on **Windows Smart App Control**. It explains that since the app is unsigned, they must click "More Info" -> "Run Anyway" or authorize the process.
3.  **The Downloader:** Provides a one-click button to fetch the Creative Engines (Custom, Base, Design) directly from HuggingFace.
4.  **Finish:** Sets expectations that the *very first* launch will take ~2 minutes to load into VRAM.

### Phase C: Studio Launch
*   The wizard exits and spawns the main UI (`PRO_QWEN.py` logic).
*   The `app.lock` is created to ensure only one instance of the heavy AI engine is active.

---

## 2. Running from the Terminal

Advanced users may want to run the app via the command line to see debug output or logs.

1.  Open **PowerShell** or **CMD**.
2.  Navigate to the folder: `cd "C:\Path\To\Your\Extracted\Folder"`
3.  Execute the binary:
    ```powershell
    .\Qwen3_Studio_Pro.exe
    ```
*Note: If there are any crashes, the terminal will stay open and show the Python traceback, which is helpful for troubleshooting.*

---

## 3. Creating a Desktop Shortcut (Batch Script)

Since we are using **Directory Mode** (where the EXE lives next to an `_internal` folder), you can create a simple `.bat` file on your desktop to launch the app without navigating through folders.

### How to create it:
1.  Right-click your Desktop -> **New** -> **Text Document**.
2.  Name it `Launch_Qwen_Studio.bat` (make sure the extension changes from `.txt` to `.bat`).
3.  Paste the following code (edit the path to match your install location):

```batch
@echo off
title Qwen3 Studio Launcher
:: CHANGE THE PATH BELOW TO YOUR ACTUAL FOLDER
set "APP_PATH=C:\Users\YourName\Desktop\Qwen3_Studio"

cd /d "%APP_PATH%"
start "" "Qwen3_Studio_Pro.exe"
exit
```

### Why use a Batch Script?
*   **Convenience:** One-click access from the desktop.
*   **Path Stability:** Ensures the working directory is always correct, so the app finds the `sox` and `engine` folders every time.
*   **Administrative Rights:** If needed, you can right-click this `.bat` file and "Run as Administrator" to bypass certain folder permission issues.

---
© 2026 Blues Creative Engineering.
