[Setup]
; --- APP INFO ---
AppName=Qwen3 TTS Pro
AppVersion=3.6
AppPublisher=Blues Lab
AppPublisherURL=https://www.blues-lab.pro

; --- INSTALLATION SETTINGS ---
; This installs to C:\Program Files\Qwen3 Studio
DefaultDirName={autopf}\Qwen3 Studio
DefaultGroupName=Qwen3 Studio

; --- OUTPUT SETTINGS ---
; This names the final installer "Pro_Studio_Setup_v3.6.exe"
OutputBaseFilename=Pro_Studio_Setup_v3.6
; This creates the installer in a folder named "Output"
OutputDir=Output
Compression=lzma2
SolidCompression=yes
; Points to your icon (make sure pq.ico is in your project folder)
SetupIconFile=pq.ico

[Files]
; --- CRITICAL PART ---
; This tells the installer: "Take EVERYTHING inside dist/Qwen3_Studio and pack it."
; Make sure the path matches your folder structure!
Source: "dist\Qwen3_Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; --- SHORTCUTS ---
; We create a Desktop Shortcut that points to the LAUNCHER, not the main app.
Name: "{autodesktop}\Qwen3 Studio"; Filename: "{app}\app_launcher.exe"; IconFilename: "{app}\Qwen3_Studio.exe"
Name: "{autoprograms}\Qwen3 Studio"; Filename: "{app}\app_launcher.exe"; IconFilename: "{app}\Qwen3_Studio.exe"

[Run]
; Auto-run the launcher after installation finishes
Filename: "{app}\app_launcher.exe"; Description: "Launch Qwen3 Studio"; Flags: nowait postinstall skipifsilent