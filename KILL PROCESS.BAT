@echo off
echo Terminating Qwen3 Launcher and associated Python processes...
taskkill /IM pythonw.exe /F 2>nul
taskkill /IM Qwen3_Launcher.exe /F 2>nul
echo Process termination complete.