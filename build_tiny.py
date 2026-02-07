import PyInstaller.__main__

print("🚀 Building Qwen3 Launcher...")

PyInstaller.__main__.run([
    'tiny_loader.py',           # The script that downloads from Hugging Face
    '--name=Qwen3_Launcher',    # <--- NEW CORRECT NAME
    '--onefile',                # Single file
    '--noconsole',              # No black window
    '--clean',
    '--icon=pq.ico'             # Your icon
])

print("✅ DONE! Check dist/ folder for Qwen3_Launcher.exe")