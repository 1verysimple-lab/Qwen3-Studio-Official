# Qwen3 Pro Suite - Visual Installer
# Created by Blues Creative Engineering

$AppName = "Qwen3 Pro Suite"
$InstallDir = "$HOME\Qwen3Pro"
$SourceDir = $PSScriptRoot

Clear-Host
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   $AppName - Installation Wizard" -ForegroundColor White
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verification
if (!(Test-Path "$SourceDir\Pro_Studio_Launcher.py") -and !(Test-Path "$SourceDir\dist\Qwen3_Studio_Pro.exe")) {
    Write-Host "Error: Installation files not found in $SourceDir" -ForegroundColor Red
    pause
    exit
}

Write-Host "Preparing to install to: $InstallDir" -ForegroundColor Gray
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 2. File List (Everything needed for the app)
$ItemsToCopy = @("engine", "sox", "modules", "tutorials", "version.json", "pq.ico", "PRO_QWEN.py", "Pro_Studio_Launcher.py", "config_manager.py", "batch_director.py")

# 3. Copy with Progress
$i = 0
foreach ($Item in $ItemsToCopy) {
    $i++
    $Percent = ($i / $ItemsToCopy.Count) * 100
    Write-Progress -Activity "Installing $AppName" -Status "Copying $Item..." -PercentComplete $Percent
    
    $Src = Join-Path $SourceDir $Item
    if (Test-Path $Src) {
        Copy-Item -Path $Src -Destination $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Progress -Activity "Installing $AppName" -Completed

# 4. Create Desktop Shortcut
Write-Host "Creating shortcuts..." -ForegroundColor Gray
$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
# If we have the compiled EXE, use it. Otherwise use the launcher script.
if (Test-Path "$InstallDir\dist\Qwen3_Studio_Pro.exe") {
    $Shortcut.TargetPath = "$InstallDir\dist\Qwen3_Studio_Pro.exe"
} else {
    $Shortcut.TargetPath = "pythonw.exe"
    $Shortcut.Arguments = "`"$InstallDir\Pro_Studio_Launcher.py`""
}
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = "$InstallDir\pq.ico"
$Shortcut.Save()

# 5. Finish
Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "   INSTALLATION COMPLETE!" -ForegroundColor White
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "You can now find $AppName on your Desktop."

$Choice = Read-Host "Would you like to launch the app now? (Y/N)"
if ($Choice -eq 'Y' -or $Choice -eq 'y') {
    if (Test-Path "$InstallDir\dist\Qwen3_Studio_Pro.exe") {
        Start-Process "$InstallDir\dist\Qwen3_Studio_Pro.exe"
    } else {
        Start-Process "pythonw.exe" -ArgumentList "`"$InstallDir\Pro_Studio_Launcher.py`""
    }
}
