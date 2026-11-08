; Installer for Sweep (Python + Qt build). Compiled by GitHub Actions.
; /DBeta=1 builds Sweep Beta: another program next to Sweep (own AppId, folder, shortcuts, scheduled tasks).
#ifdef Beta
  #define AppName "Sweep Beta"
  #define SetupName "Sweep-Beta-Setup"
#else
  #define AppName "Sweep"
  #define SetupName "Sweep-Setup"
#endif
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef NumVersion
  #define NumVersion AppVersion
#endif

[Setup]
#ifdef Beta
AppId={{3B9F6D2E-8A41-4E7C-B5D0-2C6E9F1A7B83}
#else
AppId={{7E2C1C3A-5B61-4C7B-9D1E-0A7A1F2B3C4D}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Sweep
AppPublisherURL=https://github.com/drakedog-dev/sweep
AppCopyright=Copyright (c) 2026 Alex (Drakedog). MIT License.
VersionInfoVersion={#NumVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#NumVersion}
VersionInfoCompany=Sweep
VersionInfoDescription={#AppName} Setup
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\Sweep.exe
OutputDir=Output
OutputBaseFilename={#SetupName}-{#AppVersion}
SetupIconFile=sweep.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"; LicenseFile: "installer\terms-en.txt"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"; LicenseFile: "installer\terms-ru.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Sweep\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Sweep.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Sweep.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Sweep.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent shellexec
; silent self-update started from inside Sweep: relaunch the app when asked to
Filename: "{app}\Sweep.exe"; Flags: nowait shellexec; Check: ShouldRelaunch

[UninstallRun]
; scheduled tasks Sweep created (Guard and the weekly clean) leave together with Sweep
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""{#AppName} Guard"" /F"; Flags: runhidden; RunOnceId: "DelGuardTask"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""{#AppName} Auto Clean"" /F"; Flags: runhidden; RunOnceId: "DelAutoTask"

[Code]
function ShouldRelaunch: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:RELAUNCH|0}') = '1');
end;

[InstallDelete]
; files of the old PowerShell build
Type: files; Name: "{app}\sweep.ico"
Type: files; Name: "{app}\README.md"
