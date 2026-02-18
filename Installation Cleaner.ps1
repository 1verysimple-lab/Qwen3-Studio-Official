# ==========================================================
# Qwen3 Studio - Environment Reset Script
# ========================== [cite: 2026-02-09] ============

$ErrorActionPreference = "SilentlyContinue"

Write-Host "--- Initiating Deep Clean ---" -ForegroundColor Cyan

# 1. Kill any hung Qwen3 processes
Write-Host "Stopping any running instances..."
Stop-Process -Name "Qwen3_Launcher" -Force
Stop-Process -Name "pythonw" -Force

# 2. Wipe the AppData Root
$AppDataPath = "$env:LOCALAPPDATA\Qwen3Studio"
if (Test-Path $AppDataPath) {
    Write-Host "Removing AppData: $AppDataPath"
    Remove-Item -Recurse -Force $AppDataPath
}

# 3. Remove the Desktop Shortcut
$Shortcut = "$env:USERPROFILE\Desktop\Qwen3 Studio.lnk"
if (Test-Path $Shortcut) {
    Write-Host "Removing Shortcut: $Shortcut"
    Remove-Item -Force $Shortcut
}

# 4. Purge PyInstaller Temporary Files
Write-Host "Clearing temp build artifacts..."
Remove-Item -Recurse -Force "$env:TEMP\_MEI*"

# 5. Clean local build folders
Remove-Item -Recurse -Force "build", "dist"

Write-Host "--- System Clean. Ready for Fresh Test. ---" -ForegroundColor Green
Pause