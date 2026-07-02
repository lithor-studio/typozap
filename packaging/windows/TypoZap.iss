#define MyAppName "TypoZap"
#define MyAppVersion "2.0.0"
#define MyAppExeName "TypoZap.exe"

[Setup]
AppId={{0A7AEB22-C2AD-4B65-B023-C4613D742CF4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=TypoZap-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\..\dist\TypoZap.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\TypoZap"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TypoZap"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le bureau"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer TypoZap"; Flags: nowait postinstall skipifsilent
