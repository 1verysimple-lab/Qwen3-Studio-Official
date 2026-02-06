import PyInstaller.__main__
import shutil
import os
import time

def build():
    start_time = time.time()
    work_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(work_dir, "dist")
    final_output = os.path.join(dist_dir, "Qwen3_Studio")
    
    # 1. CLEANUP
    print("STEP 1: Cleaning...")
    if os.path.exists(dist_dir): shutil.rmtree(dist_dir)
    if os.path.exists("build"): shutil.rmtree("build")

    # 2. BUILD MAIN APP (Folder Mode)
    print("STEP 2: Building Main Studio (Folder Mode)...")
    PyInstaller.__main__.run([
        'app_main.py',
        '--name=Qwen3_Studio',
        '--onedir',             # Important: Folder mode
        '--noconsole',
        '--clean',
        '--icon=pq.ico',
        '--add-data=tutorials;tutorials',
        '--add-data=sox;sox',
        '--add-data=version.json;.',
        '--hidden-import=scipy.special.cython_special'
    ])

    # 3. BUILD LAUNCHER (OneFile Mode)
    print("STEP 3: Building Launcher (OneFile)...")
    PyInstaller.__main__.run([
        'app_launcher.py',
        '--name=app_launcher',
        '--onefile',            # Important: Single EXE
        '--noconsole',
        '--clean',
        '--icon=pq.ico'
    ])

    # 4. MERGE
    print("STEP 4: Merging Launcher into Studio Folder...")
    # Move the launcher exe from dist/app_launcher.exe to dist/Qwen3_Studio/app_launcher.exe
    src_launcher = os.path.join(dist_dir, "app_launcher.exe")
    dst_launcher = os.path.join(final_output, "app_launcher.exe")
    
    if os.path.exists(src_launcher):
        shutil.move(src_launcher, dst_launcher)
    else:
        print("ERROR: Launcher build failed!")

    print(f"\nBUILD COMPLETE in {int(time.time() - start_time)}s")
    print(f"Final App Location: {final_output}")
    print("You can now zip this folder for 'Portable' release,")
    print("or run Inno Setup on it for the 'Installer' release.")

if __name__ == "__main__":
    build()