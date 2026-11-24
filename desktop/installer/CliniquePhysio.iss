; Windows installer for the front-desk desktop app (Inno Setup 6).
; Built by .github/workflows/release.yml:
;   iscc /DAppVersion=1.0.0 /DSourceDir=..\..\publish desktop\installer\CliniquePhysio.iss
; Installs for the current user only (no administrator rights needed), in French or English.
; The installer is not code-signed (student project): Windows SmartScreen shows
; "Windows protected your PC" the first time; click "More info" then "Run anyway".

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\publish"
#endif

#define AppName "Clinique Physio Mont-Royal - Accueil"
#define AppExe "CliniquePhysio.Desktop.exe"

[Setup]
; Fixed id: a newer version replaces the older one instead of installing beside it.
AppId={{6E0C1B7A-4F5D-4B8E-9C2A-31D7A0F4C9B2}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=KK
AppPublisherURL=https://github.com/stevatak/Khadizhat-Synth
DefaultDirName={localappdata}\Programs\CliniquePhysioAccueil
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\installer-output
OutputBaseFilename=CliniquePhysio-Accueil-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Self-contained publish: .NET does not need to be installed on the computer.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Excludes: "appsettings.json,*.pdb"; Flags: ignoreversion recursesubdirs createallsubdirs
; appsettings.json (API address): installed once, then kept, so a changed address survives updates.
Source: "{#SourceDir}\appsettings.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
