; ============================================================
; PyPlayer Compressor 10MB - Inno Setup Installer Script
; Compatible with PyInstaller 6.x+ (_internal folder structure)
; ============================================================
; ใช้สำหรับสร้าง installer สำหรับ Windows
; ต้องการ: Inno Setup 6.x หรือใหม่กว่า (https://jrsoftware.org/isdl.php)
; ============================================================

#define AppName "PyPlayer Compressor 10MB"
#define AppVersion "0.6.0 beta"
#define AppPublisher "Piyabordee"
#define AppPublisherURL "https://github.com/Piyabordee/pyplayer-compressor-10mb"
#define AppSupportURL "https://github.com/Piyabordee/pyplayer-compressor-10mb/issues"
#define AppUpdatesURL "https://github.com/Piyabordee/pyplayer-compressor-10mb/releases"
#define AppExeName "pyplayer.exe"

[Setup]
; ข้อมูลพื้นฐานของแอปพลิเคชัน
AppId={{A1B2C3D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppPublisherURL}
AppSupportURL={#AppSupportURL}
AppUpdatesURL={#AppUpdatesURL}

; การติดตั้ง
DefaultDirName={autopf}\PyPlayer Compressor
DefaultGroupName=PyPlayer Compressor
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=PyPlayerCompressor-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
InternalCompressLevel=max

; ตั้งค่าความปลอดภัยและ permissions
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\pyplayer.exe
CreateAppDir=yes
DisableDirPage=no
DisableProgramGroupPage=yes

; ไฟล์และโฟลเดอร์พิเศษ
UsePreviousAppDir=yes
UsePreviousGroup=yes
DisableWelcomePage=no

; ข้อมูลเพิ่มเติม
AppCopyright=Copyright (C) 2024 {#AppPublisher}
AppComments=Video player and compressor with FFmpeg
AppContact={#AppSupportURL}
VersionInfoVersion=0.6.0.0
VersionInfoCompany={#AppPublisher}

; UI/UX
WizardStyle=modern
SetupIconFile=..\themes\resources\logo.ico
UninstallIconFile=..\themes\resources\logo.ico
ShowLanguageDialog=no
; NOTE: WizardImageFile ต้องเป็น .bmp ถ้าไม่มีสามารถ comment out ได้
;WizardImageFile=..\themes\resources\logo_filled.bmp
;WizardSmallImageFile=..\themes\resources\logo_outline.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "thai"; MessagesFile: "compiler:Languages\Thai.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "associate"; Description: "Associate video and audio files with PyPlayer Compressor"; GroupDescription: "File associations:"
Name: "autoplay"; Description: "Auto-play videos when opened"; GroupDescription: "Behavior:"; Flags: unchecked

[Files]
; ============================================================
; PyInstaller 6.x onedir structure:
; pyplayer.exe (main executable)
; _internal/ (all dependencies)
; ============================================================
; NOTE: Paths are relative to the .iss file location (executable/)

; Main executable
Source: "compiling\release\pyplayer.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: Main
Source: "compiling\updater.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: Main

; All files from _internal folder (PyInstaller 6.x structure)
Source: "compiling\release\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs; Components: Main

; NOTE: PyInstaller 6.x bundles everything in _internal including:
; - PyQt5
; - Python runtime (python313.dll)
; - VLC and FFmpeg binaries (in plugins/)
; - All dependencies

[Icons]
; Start Menu shortcuts
Name: "{group}\PyPlayer Compressor"; Filename: "{app}\pyplayer.exe"; IconFilename: "{app}\pyplayer.exe"; Comment: "Video player and compressor"
Name: "{group}\Uninstall PyPlayer Compressor"; Filename: "{uninstallexe}"; IconFilename: "{uninstallexe}"

; Desktop shortcut (optional)
Name: "{autodesktop}\PyPlayer Compressor"; Filename: "{app}\pyplayer.exe"; Tasks: desktopicon; IconFilename: "{app}\pyplayer.exe"

; Quick Launch (Windows 7 และก่อนหน้า)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\PyPlayer Compressor"; Filename: "{app}\pyplayer.exe"; Tasks: quicklaunchicon

[Registry]
; File associations (ถ้าเลือก task "associate")
Root: HKCR; Subkey: ".mp4"; ValueType: string; ValueName: ""; ValueData: "PyPlayerCompressor.mp4"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mp4"; ValueType: string; ValueName: ""; ValueData: "MP4 Video File"; Flags: uninsdeletekey; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mp4\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pyplayer.exe,0"; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mp4\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pyplayer.exe"" ""%1"""; Tasks: associate

Root: HKCR; Subkey: ".avi"; ValueType: string; ValueName: ""; ValueData: "PyPlayerCompressor.avi"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.avi"; ValueType: string; ValueName: ""; ValueData: "AVI Video File"; Flags: uninsdeletekey; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.avi\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pyplayer.exe,0"; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.avi\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pyplayer.exe"" ""%1"""; Tasks: associate

Root: HKCR; Subkey: ".mkv"; ValueType: string; ValueName: ""; ValueData: "PyPlayerCompressor.mkv"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mkv"; ValueType: string; ValueName: ""; ValueData: "MKV Video File"; Flags: uninsdeletekey; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mkv\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pyplayer.exe,0"; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mkv\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pyplayer.exe"" ""%1"""; Tasks: associate

Root: HKCR; Subkey: ".mp3"; ValueType: string; ValueName: ""; ValueData: "PyPlayerCompressor.mp3"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mp3"; ValueType: string; ValueName: ""; ValueData: "MP3 Audio File"; Flags: uninsdeletekey; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mp3\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pyplayer.exe,0"; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.mp3\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pyplayer.exe"" ""%1"""; Tasks: associate

Root: HKCR; Subkey: ".wav"; ValueType: string; ValueName: ""; ValueData: "PyPlayerCompressor.wav"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.wav"; ValueType: string; ValueName: ""; ValueData: "WAV Audio File"; Flags: uninsdeletekey; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.wav\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pyplayer.exe,0"; Tasks: associate
Root: HKCR; Subkey: "PyPlayerCompressor.wav\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pyplayer.exe"" ""%1"""; Tasks: associate

; Auto-play setting (ถ้าเลือก task "autoplay")
Root: HKCU; Subkey: "Software\Piyabordee\PyPlayer Compressor"; ValueType: dword; ValueName: "AutoPlay"; ValueData: "1"; Tasks: autoplay

[Run]
; เปิดโปรแกรมหลังจากติดตั้งเสร็จ (ถ้าผู้ใช้เลือก)
Filename: "{app}\pyplayer.exe"; Description: "Launch PyPlayer Compressor now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; ลบไฟล์ที่สร้างขึ้นระหว่าง runtime
Type: filesandordirs; Name: "{app}\_internal\temp"
Type: filesandordirs; Name: "{app}\config.ini"
Type: files; Name: "{app}\pyplayer.log"

[Components]
Name: "Main"; Description: "Main Program Files"; Types: full compact custom; Flags: fixed

[Types]
Name: "full"; Description: "Full installation"
Name: "compact"; Description: "Compact installation"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Code]
// Pascal script สำหรับการตรวจสอบและการตั้งค่าเพิ่มเติม

procedure CurStepChanged(CurStep: TSetupStep);
begin
  // หลังจากการติดตั้งเสร็จสิ้น
  if CurStep = ssPostInstall then
  begin
    // สร้างโฟลเดอร์ temp สำหรับ application
    if not DirExists(ExpandConstant('{app}\_internal\temp')) then
      ForceDirectories(ExpandConstant('{app}\_internal\temp'));
  end;
end;

// ตรวจสอบว่ามีการติดตั้งเก่าอยู่หรือไม่
function IsUpgrade(): Boolean;
var
  sPrevPath: String;
begin
  sPrevPath := '';
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\A1B2C3D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D_is1', 'UninstallString', sPrevPath) then
    Result := True
  else if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\A1B2C3D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D_is1', 'UninstallString', sPrevPath) then
    Result := True
  else
    Result := False;
end;

// แสดงข้อความเมื่อพบว่ามีการติดตั้งเก่า
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpWelcome) and IsUpgrade() then
    if MsgBox('An older version of PyPlayer Compressor is detected. It will be uninstalled automatically before the new version is installed. Do you want to continue?', mbInformation, MB_YESNO) = IDNO then
      Result := False;
end;
