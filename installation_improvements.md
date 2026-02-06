# Installation Improvements: Qwen3 Studio Pro

This document outlines proposed enhancements to the Setup Wizard to provide better transparency, control, and reliability during the initial engine download (approx. 15GB).

## 1. Problem Statement
The current installation process is "silent." Users have no visual feedback on download progress, speed, or estimated time remaining. If the window is closed, the process remains active in the background, creating a "ghost" instance that prevents the app from restarting due to the `launcher.lock` file.

## 2. Proposed Solutions

### A. Visual Progress Feedback
- **Progress Bar:** A standard progress bar showing percentage completion.
- **Data Metrics:** Display "MB/GB Downloaded" vs "Total Size" (e.g., `4.2GB / 15.0GB`).
- **Speed & ETA:** Show current download speed (MB/s) and estimated time remaining.
- **Step Indicator:** Clearly label which engine is being fetched (Base, Creative, or Design).

### B. Process Control (Cancel/Resume)
- **Cancel Button:** Allow users to safely stop the download. This should trigger a cleanup of partial files and a graceful exit of the process.
- **Resume Support:** Implement "Check-pointing." If the app is closed and restarted, it should verify existing files (using file size or hashes) and resume from where it left off rather than starting over.

### C. Smart Locking Mechanism
- **Active UI Check:** If the main window is closed, the background download should either stop gracefully or prompt the user: *"Download is still in progress. Continue in background?"*
- **Lock Cleanup:** If the app crashes, the next launch should detect if the process ID in the lock file is actually still running. If not, it should automatically clear the lock.

---

## 3. User FAQ: "What do I do if I closed the installer?"

### Q: What should I do next if I closed the window?
**A:** Since the process often stays alive in the background, you must first ensure it is fully stopped. 
1. Open **Task Manager** (Ctrl+Shift+Esc).
2. Look for `Qwen3_Studio_Pro.exe` and click **End Task**.
3. Delete the `launcher.lock` file in the application folder.
4. Restart the app.

### Q: Will it continue or start over?
**A:** Most modern Python download libraries (like `huggingface_hub`, which this app uses) are designed to resume. It will "scan" the 4.2GB you already have, realize they are complete, and start downloading the remaining ~10.8GB. It might look like it's stuck for a minute while it scans, but it is actually saving you time.

### Q: Why is there no "Cancel" button?
**A:** In the current version, the "Download" trigger is a simple execution command. Adding a Cancel button requires "Asynchronous Task Management"—basically, the app needs to be able to talk to the downloader while it's busy. This is a priority for the next update.

### Q: How do I know if it's working now?
**A:** For now, the best way to see the "truth" is to run the app from a **Terminal** (PowerShell). 
- Right-click in the folder -> **Open in Terminal**.
- Type `.\Qwen3_Studio_Pro.exe` and press Enter.
- You will see the text-based progress bars that the app usually hides.
