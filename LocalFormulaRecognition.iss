; Inno Setup 安装包脚本：本地数学公式识别工具
; 用法：本机安装 Inno Setup 6 后，执行 ISCC.exe LocalFormulaRecognition.iss

#define AppName "本地数学公式识别工具"
#define AppNameEn "LocalFormulaRecognition"
#define AppVersion "1.0.0"
#define AppPublisher "LocalFormulaRecognition"
#define SourceDir "dist\LocalFormulaRecognition"

[Setup]
AppId={{B7F3A2C1-4E58-4D9A-9C6E-1A2B3C4D5E6F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppNameEn}
DefaultGroupName={#AppName}
OutputDir=installer
OutputBaseFilename=LocalFormulaRecognition-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
DisableProgramGroupPage=no
UninstallDisplayName={#AppName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："

[Files]
Source: "{#SourceDir}\LocalFormulaRecognition.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppNameEn}.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppNameEn}.exe"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#AppNameEn}.exe"; Description: "立即运行 {#AppName}"; Flags: nowait postinstall skipifsilent