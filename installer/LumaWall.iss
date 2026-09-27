#define MyAppName "LumaWall"
#define MyAppPublisher "LumaWall"
#define MyAppExeName "LumaWall.exe"

; The version is read from the built exe, not written here.
;
; Why: this file used to carry its own version string, and the two drifted. The
; installer said 4.1.3 while the exe inside it reported 4.1.2.0, so the Add/Remove
; Programs entry named a version that was not the one installed. Reading it from
; the binary makes that impossible - there is one number, and it belongs to the
; thing being installed.
;
; GetVersionNumbersString returns the FileVersion resource, which the build sets
; from AssemblyInfo.cs.
#define MyAppVersion GetVersionNumbersString(AddBackslash(SourcePath) + "..\LumaWall\bin\Release\LumaWall.exe")

[Setup]
AppId={{6CC7BEB4-4F78-4BA8-A109-C23DB7598C51}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\outputs
OutputBaseFilename=LumaWall-Setup-{#MyAppVersion}
SetupIconFile=..\LumaWall\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\LumaWall\LICENSE.txt
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=4.1.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=LumaWall Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
MinVersion=10.0.17763

[Tasks]
Name: "startup"; Description: "Jalankan LumaWall otomatis saat masuk Windows"; GroupDescription: "Opsi startup:" 
Name: "desktopicon"; Description: "Buat pintasan di desktop"; GroupDescription: "Pintasan tambahan:"; Flags: unchecked

[Files]
Source: "..\LumaWall\bin\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LumaWall"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall LumaWall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LumaWall"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LumaWall"; ValueData: """{app}\{#MyAppExeName}"" --background"; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan LumaWall"; Flags: nowait postinstall skipifsilent
