; Установщик Sweep для Inno Setup 6. Открыть этот файл в Inno Setup и нажать Build (Ctrl+F9),
; или запустить build-setup.bat. На выходе: Output\Sweep-Setup-0.3.exe

#define AppName "Sweep"
#define AppVersion "0.6"

[Setup]
AppId={{7E2C1C3A-5B61-4C7B-9D1E-0A7A1F2B3C4D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Sweep
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\Sweep.exe
OutputDir=Output
OutputBaseFilename=Sweep-Setup-{#AppVersion}
SetupIconFile=sweep.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "Sweep.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "sweep.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Sweep.exe"; IconFilename: "{app}\sweep.ico"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Sweep.exe"; IconFilename: "{app}\sweep.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\Sweep.exe"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent shellexec
