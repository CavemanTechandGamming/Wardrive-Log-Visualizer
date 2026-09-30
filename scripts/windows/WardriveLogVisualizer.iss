; Wardrive Log Visualizer — Inno Setup script
; Compile via build_app.bat (passes MyAppVersion, MyAppSource, MyAppOutput).
;
; Required defines (from ISCC /D...):
;   MyAppVersion  e.g. 0.0.1
;   MyAppSource   absolute path to PyInstaller onedir folder
;   MyAppOutput   absolute path for Setup.exe output directory

#ifndef MyAppVersion
  #error MyAppVersion must be passed with /DMyAppVersion=x.y.z
#endif
#ifndef MyAppSource
  #error MyAppSource must be passed with /DMyAppSource=...
#endif
#ifndef MyAppOutput
  #error MyAppOutput must be passed with /DMyAppOutput=...
#endif

#define MyAppName "Wardrive Log Visualizer"
#define MyAppPublisher "Wardrive Log Visualizer"

#ifndef MyAppExeName
  #define MyAppExeName "WardriveLogVisualizer-" + MyAppVersion + ".exe"
#endif

[Setup]
AppId={{FE331B61-8103-4B19-A81A-FDD568D85FD7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MyAppOutput}
OutputBaseFilename=WardriveLogVisualizer-{#MyAppVersion}-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
#ifdef MyAppIcon
SetupIconFile={#MyAppIcon}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
