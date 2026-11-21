; SPDX-FileCopyrightText: 2026 AbuKaram01
; SPDX-License-Identifier: AGPL-3.0-or-later
;
; Inno Setup script for the Windows installer. Build it with packaging\build-windows.ps1.
;
; The installer ships KaramWS's own files, the GTK 4 + libadwaita runtime, Python's installer, the Python libraries
; (a "wheelhouse") and the Chromium that Playwright drives, when packaging\build-windows.ps1 prepared them. After
; copying them it runs scripts\install-windows.ps1, which installs Python (when it is missing), creates the Python
; environment and installs the libraries from the wheelhouse, and downloads only what the installer does not carry.
; Everything is per user: no administrator rights are required.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppName "KaramWS"
#define AppId "io.github.AbuKaram01.KaramWS"

[Setup]
AppId={{BF4D1247-42A1-417E-9C68-FD390B9F13E2}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=AbuKaram01
AppPublisherURL=https://github.com/AbuKaram01/KaramWS
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE
SetupIconFile=..\..\data\windows\karamws.ico
UninstallDisplayIcon={app}\data\windows\karamws.ico
OutputDir=..\dist
OutputBaseFilename=karamws-{#AppVersion}-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "..\..\src\*"; DestDir: "{app}\src"; Excludes: "__pycache__,*.pyc,*.egg-info"; Flags: recursesubdirs ignoreversion
Source: "..\..\data\*"; DestDir: "{app}\data"; Flags: recursesubdirs ignoreversion
Source: "..\..\scripts\install-windows.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\..\scripts\gtk-portable.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\..\scripts\browsers-portable.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\..\scripts\python-bundle.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\..\scripts\uninstall-windows.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; The GTK 4 + libadwaita runtime that packaging\build-windows.ps1 prepared: installed beside the application, where
; the application finds it by itself, so that it does not have to be downloaded. The install script uses it when it is
; there and downloads one only when it is not.
#define GtkFolder SourcePath + "\..\gtk"
#if DirExists(GtkFolder)
Source: "{#GtkFolder}\*"; DestDir: "{app}\gtk"; Flags: recursesubdirs ignoreversion
#endif

; The python.org installer of the Python that the GTK runtime's wheels are for: the install script runs it, silently and
; for the current user, when that Python is missing, so that winget is not needed.
#define PythonFolder SourcePath + "\..\python"
#if DirExists(PythonFolder)
Source: "{#PythonFolder}\*"; DestDir: "{app}\python"; Flags: recursesubdirs ignoreversion
#endif

; The Python libraries (wheels) that packaging\build-windows.ps1 prepared: the install script installs them without
; internet access.
#define WheelFolder SourcePath + "\..\wheelhouse"
#if DirExists(WheelFolder)
Source: "{#WheelFolder}\*"; DestDir: "{app}\wheelhouse"; Flags: recursesubdirs ignoreversion
#endif

; The Chromium that Playwright drives, prepared by packaging\build-windows.ps1 from the Playwright of the wheelhouse:
; installed beside the application's Python environment, where the program finds it by itself (the install script
; downloads one only when it is not there), so that pages that need JavaScript work without the internet.
#define BrowsersFolder SourcePath + "\..\browsers"
#if DirExists(BrowsersFolder)
Source: "{#BrowsersFolder}\*"; DestDir: "{app}\browsers"; Flags: recursesubdirs ignoreversion
#endif

; The Visual C++ runtime DLLs (msvcp140.dll ...) that packaging\build-windows.ps1 collected: the libraries that need them
; do not load on a computer that lacks the Visual C++ Redistributable. The application loads these before anything
; else (src\karamws\winsupport.py).
#define VcRuntimeFolder SourcePath + "\..\vcruntime"
#if DirExists(VcRuntimeFolder)
Source: "{#VcRuntimeFolder}\*"; DestDir: "{app}\vcruntime"; Flags: recursesubdirs ignoreversion
#endif

[InstallDelete]
#if DirExists(GtkFolder)
; An upgrade starts from an empty runtime folder, so that no file of an older runtime stays beside the new DLLs.
Type: filesandordirs; Name: "{app}\gtk"
#endif
#if DirExists(PythonFolder)
Type: filesandordirs; Name: "{app}\python"
#endif
#if DirExists(WheelFolder)
Type: filesandordirs; Name: "{app}\wheelhouse"
#endif
#if DirExists(BrowsersFolder)
Type: filesandordirs; Name: "{app}\browsers"
#endif
#if DirExists(VcRuntimeFolder)
Type: filesandordirs; Name: "{app}\vcruntime"
#endif

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: "-m karamws.gui"; WorkingDir: "{app}"; IconFilename: "{app}\data\windows\karamws.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: "-m karamws.gui"; WorkingDir: "{app}"; IconFilename: "{app}\data\windows\karamws.ico"; Tasks: desktopicon

[Registry]
; The application registers its notification identity here at run time; this makes the uninstaller remove it.
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\{#AppId}"; Flags: uninsdeletekey

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\src"
Type: filesandordirs; Name: "{app}\build"
Type: filesandordirs; Name: "{app}\gtk"
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\wheelhouse"
Type: filesandordirs; Name: "{app}\browsers"
Type: filesandordirs; Name: "{app}\vcruntime"
; The GTK runtime an install script downloaded (when the installer did not carry one). The articles you saved are
; never removed.
Type: filesandordirs; Name: "{localappdata}\karamws\gtk"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  Parameters: String;
  ResultCode: Integer;
begin
  if CurStep <> ssPostInstall then
    Exit;
  Parameters := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\scripts\install-windows.ps1') + '" -NoShortcut -LogFile "' + ExpandConstant('{localappdata}\karamws\install.log') + '"';
#if DirExists(GtkFolder) && DirExists(PythonFolder) && DirExists(WheelFolder)
  WizardForm.StatusLabel.Caption := 'Setting up Python and its libraries (everything is already in this installer; this takes a few minutes)...';
#elif DirExists(GtkFolder)
  WizardForm.StatusLabel.Caption := 'Setting up Python and the dependencies (GTK is already in this installer; what is not is downloaded)...';
#else
  WizardForm.StatusLabel.Caption := 'Setting up GTK, Python and the dependencies (about a gigabyte is downloaded)...';
#endif
  if (not Exec('powershell.exe', Parameters, ExpandConstant('{app}'), SW_SHOW, ewWaitUntilTerminated, ResultCode)) or (ResultCode <> 0) then
    MsgBox('KaramWS was copied, but its components could not be set up.' + #13#10 + #13#10 +
           'What went wrong is written in ' + ExpandConstant('{localappdata}\karamws\install.log') + #13#10 + #13#10 +
           'Check your internet connection and run this again from a PowerShell window:' + #13#10 +
           'powershell -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\scripts\install-windows.ps1') + '"',
           mbError, MB_OK);
end;
