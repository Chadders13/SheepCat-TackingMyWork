; SheepCat – Tracking My Work
; Inno Setup Installer Script
;
; Prerequisites
; -------------
;   1. Build the Python application with PyInstaller first:
;        pyinstaller SheepCat.spec
;      This produces the deployment folder at  dist\SheepCat\
;
;   2. Download the official Ollama installer and place it at:
;        installer\OllamaSetup.exe
;      (available from https://ollama.com/download/windows)
;
;   3. Compile this script with Inno Setup 6+ (https://jrsoftware.org/isinfo.php):
;        iscc installer\SheepCat.iss
;
; The resulting installer is placed in  installer\Output\

#define MyAppName      "SheepCat - Tracking My Work"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "SheepCat"
#define MyAppURL       "https://github.com/Chadders13/SheepCat-TrackingMyWork"
#define MyAppExeName   "SheepCat.exe"
#define AppDirName     "SheepCat"

; Relative paths are resolved relative to the current working directory when
; the Inno Setup compiler (iscc) is invoked.  Run from the repo root:
;   iscc installer\SheepCat.iss
#define SrcAppDir      "dist\SheepCat"
#define OllamaSetup    "OllamaSetup.exe"

[Setup]
AppId={{A3F1C2D4-5E6B-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#AppDirName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=SheepCatSetup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

; Custom wizard image (replace with your own 164x314 px bitmap if desired)
; WizardImageFile=installer\wizard_image.bmp
; WizardSmallImageFile=installer\wizard_small.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ---------------------------------------------------------------------------
; Custom page: Ollama engine choice
; ---------------------------------------------------------------------------
[Code]

var
  OllamaPage: TWizardPage;
  RbInstallOllama: TRadioButton;
  RbSkipOllama: TRadioButton;

{ Build the custom "AI Engine" wizard page }
procedure CreateOllamaPage;
var
  PageLabel: TLabel;
begin
  OllamaPage := CreateCustomPage(
    wpSelectTasks,
    'AI Engine Setup',
    'This application requires an AI engine to generate task summaries.'
  );

  PageLabel := TLabel.Create(OllamaPage);
  with PageLabel do
  begin
    Parent := OllamaPage.Surface;
    Caption :=
      'We use Ollama as the local AI engine. How would you like to proceed?';
    Left   := 0;
    Top    := 8;
    Width  := OllamaPage.SurfaceWidth;
    WordWrap := True;
    AutoSize := False;
    Height := 32;
  end;

  RbInstallOllama := TRadioButton.Create(OllamaPage);
  with RbInstallOllama do
  begin
    Parent  := OllamaPage.Surface;
    Caption := 'Install the Ollama AI engine on this machine. (Recommended)';
    Left    := 0;
    Top     := 52;
    Width   := OllamaPage.SurfaceWidth;
    Checked := True;
    Font.Style := [fsBold];
  end;

  RbSkipOllama := TRadioButton.Create(OllamaPage);
  with RbSkipOllama do
  begin
    Parent  := OllamaPage.Surface;
    Caption :=
      'Skip. I already have Ollama running locally or on my network.';
    Left    := 0;
    Top     := 80;
    Width   := OllamaPage.SurfaceWidth;
  end;
end;

{ Hook called after all built-in pages are created }
procedure InitializeWizard;
begin
  CreateOllamaPage;
end;

{ Returns True when the user chose to install Ollama }
function ShouldInstallOllama: Boolean;
begin
  Result := RbInstallOllama.Checked;
end;

{ Run OllamaSetup.exe silently after the main app files have been installed }
procedure CurStepChanged(CurStep: TSetupStep);
var
  TempDir:    String;
  OllamaExe:  String;
  ResultCode: Integer;
begin
  if (CurStep = ssPostInstall) and ShouldInstallOllama then
  begin
    TempDir   := ExpandConstant('{tmp}');
    OllamaExe := TempDir + '\OllamaSetup.exe';

    { Extract the bundled Ollama installer to the temp directory }
    ExtractTemporaryFile('OllamaSetup.exe');

    { Run silently; /VERYSILENT suppresses all UI and progress windows }
    if not Exec(OllamaExe, '/VERYSILENT /NORESTART', '', SW_HIDE,
                ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox(
        'Ollama installation could not be started automatically.' + #13#10 +
        'Please install Ollama manually from https://ollama.com/download/windows',
        mbInformation, MB_OK
      );
    end;
  end;
end;

; ---------------------------------------------------------------------------
; Application files
; ---------------------------------------------------------------------------
[Files]
; --- Main application (PyInstaller --onedir output) ---
Source: "{#SrcAppDir}\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs; \
  Excludes: "*.pyc"

; --- Bundled Ollama installer (extracted to {tmp} at runtime) ---
Source: "{#OllamaSetup}"; \
  DestDir: "{tmp}"; \
  Flags: deleteafterinstall

; ---------------------------------------------------------------------------
; Start Menu / Desktop shortcuts
; ---------------------------------------------------------------------------
[Icons]
Name: "{group}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; \
  Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  Tasks: desktopicon

[Tasks]
Name: "desktopicon"; \
  Description: "Create a &desktop shortcut"; \
  GroupDescription: "Additional icons:"

; ---------------------------------------------------------------------------
; Run on finish
; ---------------------------------------------------------------------------
[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Launch {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent
