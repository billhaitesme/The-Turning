; OMEGA-ARC Windows installer (Inno Setup 6).
; Staging tree is assembled by installer\build_installer.ps1 into installer\build\staging.
; Per-user install, no admin required. Ollama is downloaded and installed silently if missing.

#define AppName "OMEGA-ARC"
#define AppVersion "0.3.2"
#define AppPublisher "The Turning (billhaitesme)"
#define AppURL "https://github.com/billhaitesme/The-Turning"

[Setup]
AppId={{7F4B2C19-8D36-4A7C-9E1B-5C0A3F6D2E81}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\OMEGA-ARC
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=OMEGA-ARC-Setup-{#AppVersion}
SetupIconFile=..\bridge\shared\icon\OMEGA-ARC.ico
UninstallDisplayIcon={app}\OMEGA-ARC.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=package\BEFORE-INSTALL.txt
OutputDir=Output

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "ollama"; Description: "Download and install &Ollama (required to run models; skipped if already installed)"; GroupDescription: "Dependencies:"; Check: not OllamaDetected

[Files]
Source: "build\staging\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\bridge\shared\icon\OMEGA-ARC.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "package\START-HERE.html"; DestDir: "{app}"; DestName: "OMEGA-ARC Guide.html"; Flags: ignoreversion
; .env is created from .env.example on first launch and preserved across upgrades.

[Icons]
Name: "{userprograms}\OMEGA-ARC"; Filename: "{app}\app\OMEGA-ARC.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\OMEGA-ARC.ico"
Name: "{userprograms}\OMEGA-ARC Guide"; Filename: "{app}\OMEGA-ARC Guide.html"
Name: "{userdesktop}\OMEGA-ARC"; Filename: "{app}\app\OMEGA-ARC.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\OMEGA-ARC.ico"; Tasks: desktopicon

[Run]
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"; StatusMsg: "Installing Ollama (model runtime)..."; Tasks: ollama; Flags: waituntilterminated
Filename: "{app}\app\OMEGA-ARC.cmd"; Description: "Launch OMEGA-ARC now (first launch downloads ~6 GB of models)"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
; user data (.env, backend\data, omega_arc.db) is intentionally left behind on uninstall

[Code]
var
  DownloadPage: TDownloadWizardPage;

function OllamaDetected: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'))
    or FileExists('C:\Program Files\Ollama\ollama.exe');
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpReady) and WizardIsTaskSelected('ollama') then begin
    DownloadPage.Clear;
    DownloadPage.Add('https://ollama.com/download/OllamaSetup.exe', 'OllamaSetup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        Result := True;
      except
        if DownloadPage.AbortedByUser then
          Log('Ollama download aborted by user.')
        else
          SuppressibleMsgBox('Ollama could not be downloaded. You can install it later from ollama.com; OMEGA-ARC will prompt on first launch.', mbInformation, MB_OK, IDOK);
        Result := True; { proceed with app install regardless }
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;
