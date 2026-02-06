# Qwen3 Studio Pro: Installer Debug Report

## **1. Environment & Process Details**
- **OS:** Windows (win32)
- **Primary Executable:** `Qwen3_Studio_Pro.exe` (PyInstaller-based, Python 3.10)
- **GUI Framework:** Tkinter (detected via `_tkinter.pyd` and active window titles)
- **Active Processes during stall:**
    - **PID 14396:** Main GUI ("Qwen3 Studio - First Run Setup"). Memory: ~110MB. Status: Responding, but idle.
    - **PID 16864:** Background worker. Memory: ~8MB. CPU: Static at 26.5s (no incremental usage).
- **Locking Mechanism:** `launcher.lock` in the root directory.

## **2. File System Observations**
The installer appears to be downloading/extracting two distinct model sets, leading to significant disk usage (~9.1 GB total in the `engine` folder).

### **Directory: `engine/custom` (Run 1)**
- **Total Size:** ~4.52 GB
- **Key Files:**
    - `model.safetensors`: 3,833,402,552 bytes
    - `speech_tokenizer/model.safetensors`: 682,293,092 bytes
- **Status:** Appeared complete, but the installer did not transition to the next state.

### **Directory: `engine/base` (Run 2)**
- **Total Size:** ~4.54 GB
- **Observation:** On restart, the installer created this new directory instead of verifying the existing `custom` directory. It duplicated the download/extraction effort.

### **Hugging Face Cache Issues**
- Local cache found in `engine/[type]/.cache/huggingface/download`.
- Global cache found in `%USERPROFILE%\.cache\huggingface\hub\models--Qwen--Qwen3-TTS-12Hz-1.7B-Base`.
- **The Bug:** Multiple `.incomplete` files (0 bytes) remained in the local project cache. The installer seems to be struggling with the handover between the `huggingface_hub` download manager and the local extraction path.

## **3. Network & I/O Analysis**
- **I/O Activity:** 0 bytes/sec read/write during the stall.
- **Network Activity:** 
    - Multiple TCP connections to `18.67.250.47` (AWS/CloudFront, likely HF CDN) were in a **`CloseWait`** state.
    - **Significance:** `CloseWait` indicates the remote server closed the connection, but the installer's local socket was never closed by the application logic. This suggests the download thread is hanging or deadlocked and not releasing resources.

## **4. The "Stopping" Hang**
- When the "Stop" button was clicked, the UI updated its text state to "Stopping," but the process tree remained alive.
- **Hypothesis:** The background thread (likely a `threading.Thread` or `multiprocessing.Process`) is not being joined/terminated correctly, or is blocked on a synchronous call to the `transformers` / `huggingface_hub` library that doesn't respect the stop signal.

## **5. Key Recommendations for the Fix**
1.  **Resume Logic:** Implement a check for `engine/custom/model.safetensors` before starting a new download to avoid the `engine/base` duplication.
2.  **Socket Timeouts:** Explicitly set timeouts for the download manager to prevent sockets from hanging in `CloseWait`.
3.  **Thread Management:** Use a `stop_event` (threading.Event) to allow the background worker to exit gracefully. If using `huggingface_hub`, ensure the `local_files_only=True` check is robust after the initial download.
4.  **Logging:** The current build produces no visible log files in `temp` or the root. Redirecting `stdout`/`stderr` to a `setup.log` would be invaluable for users.
