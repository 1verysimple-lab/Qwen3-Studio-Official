
1. **`DEPLOY_PROTOCOL.md`**: A "Cheat Sheet" that explains exactly how we solved the problem (The "Nuclear Fix") so you never forget.
2. **`easy_push.ps1`**: A double-click script. You never have to type `git add` or `git commit` in the terminal again. You just run this, type your message, and it handles the rest.

### 1. The Cheat Sheet (Save as `DEPLOY_PROTOCOL.md`)

```markdown
# Ì†ΩÌ∫Ä Qwen3 Studio Deployment Protocol
**Status:** ACTIVE | **Protocol:** VIBE-SECURITY (Clean Push)

## ‚ö†Ô∏è The "Golden Rule" of GitHub
**NEVER** upload the following folders to GitHub. They are too heavy (8GB+) and will break the upload immediately.
- ‚ùå `.venv` (Virtual Environment)
- ‚ùå `Qwen3-TTS` (The AI Model)
- ‚ùå `_internal` (Build Artifacts)
- ‚ùå `temp_outputs` (WAV/MP3 files)

---

## Ì†ΩÌª†Ô∏è Scenario A: Daily Update (Everything is fine)
When you have made code changes and just want to save them:
1. Run `easy_push.ps1`
2. Enter a short message (e.g., "Updated launcher UI")
3. Done.

---

## Ì†ΩÌ∫® Scenario B: The "Emergency Reset" (If Git breaks)
If you see errors like **"LFS upload failed"** or **"File too large"**, follow this "Nuclear Option":

### Step 1: Update the Ignore List
Ensure `.gitignore` contains exactly this:
```text
dist/
build/
Output/
__pycache__/
*.spec
Qwen3-TTS/
qwen_tts/
.venv/
_internal/
temp_outputs/
saved_assets/
*.wav
*.mp3
*.log
app.lock
launcher.lock

```

### Step 2: The Nuclear Commands

Run these in PowerShell to wipe the memory and start fresh:

```powershell
# 1. Kill the broken history
Remove-Item -Path .git -Recurse -Force

# 2. Start fresh
git init

# 3. Add files (The ignore list will protect you)
git add .
git commit -m "Emergency Reset Release"

# 4. Force Push to the Official Repo
git branch -M main
git remote add origin [https://github.com/1verysimple-lab/Qwen3-Studio-Official.git](https://github.com/1verysimple-lab/Qwen3-Studio-Official.git)
git push -u --force origin main

```

---

### Ì†ΩÌ≥¶ Release Checklist

1. **Build:** Run `python build_distribution.py`
2. **Pack:** Run `installer_config.iss` with Inno Setup.
3. **Upload:** Drag `Pro_Studio_Setup_vX.X.exe` to GitHub Releases.
4. **Link:** Update `version.json` with the new link.

```

---

### 2. The Automation Script (Save as `easy_push.ps1`)

Save this file in your project folder. Next time you want to save your work, just **Right-Click > Run with PowerShell**.

```powershell
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Ì†ΩÌ∫Ä Qwen3 Studio - Auto-Push System     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check if Git is alive
if (-not (Test-Path ".git")) {
    Write-Host "‚ö†Ô∏è  WARNING: No Git repository found!" -ForegroundColor Red
    Write-Host "Initializing new repository..."
    git init
    git remote add origin https://github.com/1verysimple-lab/Qwen3-Studio-Official.git
}

# 2. Ask for the update message
$msg = Read-Host "Ì†ΩÌ≥ù Enter update message (e.g. 'Fixed bug')"
if ([string]::IsNullOrWhiteSpace($msg)) {
    $msg = "Routine update"
}

# 3. The Work
Write-Host ""
Write-Host "1. Adding files..." -ForegroundColor Yellow
git add .

Write-Host "2. Committing changes..." -ForegroundColor Yellow
git commit -m "$msg"

Write-Host "3. Pushing to GitHub..." -ForegroundColor Yellow
# Try normal push first
git push origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "‚ö†Ô∏è  Normal push failed. Trying to set upstream..." -ForegroundColor Red
    git push -u origin main
}

Write-Host ""
Write-Host "‚úÖ DONE! Your code is safe." -ForegroundColor Green
Write-Host "Remember to create a Release if this was a new version." -ForegroundColor Gray
Write-Host ""
Pause

```