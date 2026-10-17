; Inno Setup script — per-user install, no admin rights needed.
; Built in CI: iscc /DAppVersion=1.0.0 packaging\windows\movo.iss

#ifndef AppVersion
  #define AppVersion "1.1.0"
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
AppName=Movo
AppVersion={#AppVersion}
VersionInfoVersion={#NumericVersion}
AppPublisher=Movo
DefaultDirName={localappdata}\Programs\Movo
DefaultGroupName=Movo
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=Movo-Setup-Windows-x64
SetupIconFile=..\movo.ico
UninstallDisplayIcon={app}\Movo.exe
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
Source: "..\..\dist\Movo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Movo"; Filename: "{app}\Movo.exe"
Name: "{autodesktop}\Movo"; Filename: "{app}\Movo.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Movo.exe"; Description: "{cm:LaunchProgram,Movo}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
