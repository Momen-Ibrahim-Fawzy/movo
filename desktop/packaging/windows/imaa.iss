; Inno Setup script — per-user install, no admin rights needed.
; Built in CI: iscc /DAppVersion=1.0.0 packaging\windows\imaa.iss

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
; File versions must be purely numeric (a.b.c.d); drop any "-dev" style suffix.
#define DashPos Pos("-", AppVersion)
#if DashPos > 0
  #define NumericVersion Copy(AppVersion, 1, DashPos - 1)
#else
  #define NumericVersion AppVersion
#endif

[Setup]
AppId={{8B3C2A61-4E7F-4C1B-9A55-1D2E6F7A9B30}
AppName=Imaa
AppVersion={#AppVersion}
VersionInfoVersion={#NumericVersion}
AppPublisher=Imaa
DefaultDirName={localappdata}\Programs\Imaa
DefaultGroupName=Imaa
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=Imaa-Setup-{#AppVersion}
SetupIconFile=..\imaa.ico
UninstallDisplayIcon={app}\Imaa.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
#if FileExists(AddBackslash(CompilerPath) + "Languages\Arabic.isl")
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\Imaa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Imaa"; Filename: "{app}\Imaa.exe"
Name: "{autodesktop}\Imaa"; Filename: "{app}\Imaa.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Imaa.exe"; Description: "{cm:LaunchProgram,Imaa}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
