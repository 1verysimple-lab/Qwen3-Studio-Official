import PyInstaller.__main__
import shutil
import os
import time

def build():
    start_time = time.time()
    work_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(work_dir, "dist")
    
    # 1. CLEANUP (Remove old builds to prevent stalling)
    print("STEP 1: Cleaning Workspace...")
    folders_to_clean = ["dist", "build", "Output", "_internal"]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: Could not delete {folder}: {e}")

    # 2. BUILD SINGLE EXE
    print("STEP 2: Building Unified Qwen3 Studio Installer...")
    
    PyInstaller.__main__.run([
        'app_launcher.py',              # Main Entry Point
        '--name=Qwen3_Studio_Setup',    # Output Name
        '--onefile',                    # Single EXE
        '--noconsole',                  # No Black Window
        '--clean',                      # Clear PyInstaller Cache
        '--icon=pq.ico',                # App Icon
        
        # --- ASSETS (Everything the app needs) ---
        '--add-data=tutorials;tutorials',
        '--add-data=sox;sox',
        '--add-data=version.json;.',
        '--add-data=pq.ico;.',
        
        # --- HIDDEN IMPORTS (Crucial for AI libs) ---
        '--hidden-import=app_main',     # Pack the App inside the Launcher
        '--hidden-import=scipy.special.cython_special',
        '--hidden-import=sklearn.utils._cython_blas',
        '--hidden-import=sklearn.neighbors.typedefs',
        '--hidden-import=sklearn.neighbors.quad_tree',
        '--hidden-import=sklearn.tree',
        '--hidden-import=sklearn.tree._utils'
    ])

    print(f"DONE! Build took {int(time.time() - start_time)} seconds.")
    print(f"Your Final File is: {os.path.join(dist_dir, 'Qwen3_Studio_Setup.exe')}")

if __name__ == "__main__":
    build()