; Copyright (c) 2026 The Sequence Group.
; SPDX-License-Identifier: Apache-2.0
;
; Inno Setup script for the Sequence RV Windows installer.
; Compile with scripts\make_installer_windows.cmd (requires Inno Setup 6,
; https://jrsoftware.org/isinfo.php), which passes the defines below.

#ifndef StageDir
  #error Pass /DStageDir=<built distribution root, e.g. ...\_build\stage\app>
#endif
#ifndef RepoRoot
  #error Pass /DRepoRoot=<repository root>
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; Stable AppId so upgrades replace rather than duplicate the install.
AppId={{7E6F2A41-3B9C-4D18-9A67-C0FFEE5EC001}
AppName=Sequence RV
AppVersion={#AppVersion}
AppPublisher=The Sequence Group
AppContact=software@thesequencegroup.com
DefaultDirName={autopf}\Sequence RV
DefaultGroupName=Sequence RV
DisableProgramGroupPage=yes
OutputBaseFilename=SequenceRV-{#AppVersion}-Setup
SetupIconFile={#RepoRoot}\branding\icon.ico
UninstallDisplayIcon={app}\icon.ico
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "{#RepoRoot}\branding\icon.ico"; DestDir: "{app}"

[Icons]
Name: "{group}\Sequence RV"; Filename: "{app}\bin\seqrv.cmd"; \
    WorkingDir: "{app}\bin"; IconFilename: "{app}\icon.ico"
Name: "{group}\Sequence RV (plain rv)"; Filename: "{app}\bin\rv.exe"; \
    WorkingDir: "{app}\bin"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\Sequence RV"; Filename: "{app}\bin\seqrv.cmd"; \
    WorkingDir: "{app}\bin"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Registry]
; Associate .rv session files with Sequence RV.
Root: HKA; Subkey: "Software\Classes\.rv\OpenWithProgids"; \
    ValueType: string; ValueName: "SequenceRV.Session"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\SequenceRV.Session"; \
    ValueType: string; ValueName: ""; ValueData: "Sequence RV Session"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SequenceRV.Session\DefaultIcon"; \
    ValueType: string; ValueName: ""; ValueData: "{app}\icon.ico"
Root: HKA; Subkey: "Software\Classes\SequenceRV.Session\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\bin\rv.exe"" ""%1"""
