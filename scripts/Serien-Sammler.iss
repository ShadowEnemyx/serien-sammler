#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{A03865D1-37BE-4A43-9460-A4F03AA42FE3}
AppName=Serien-Sammler
AppVersion={#AppVersion}
AppPublisher=ShadowEnemyx
AppPublisherURL=https://github.com/ShadowEnemyx/serien-sammler
DefaultDirName={localappdata}\Programs\Serien-Sammler
DefaultGroupName=Serien-Sammler
DisableProgramGroupPage=yes
OutputDir=..
OutputBaseFilename=Serien-Sammler-Windows-x64-Setup
SetupIconFile=..\assets\app-icon.ico
UninstallDisplayIcon={app}\Serien-Sammler.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\Serien-Sammler.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Serien-Sammler"; Filename: "{app}\Serien-Sammler.exe"
Name: "{autodesktop}\Serien-Sammler"; Filename: "{app}\Serien-Sammler.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\Serien-Sammler.exe"; Description: "{cm:LaunchProgram,Serien-Sammler}"; Flags: nowait postinstall skipifsilent
