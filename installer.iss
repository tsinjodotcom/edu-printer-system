[Setup]
AppId={{EduPrinterSystem}
AppName=Edu Printer System
AppVersion=1.0
AppPublisher=Your Company Name
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
DefaultDirName={autopf}\EduPrinterSystem
DefaultGroupName=Edu Printer System
AllowNoIcons=yes
LicenseFile=
OutputDir=installer
OutputBaseFilename=EduPrinterSystem-Setup-x64
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\EduPrinterService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\logo.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\.env"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "dist\.env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Edu Printer System"; Filename: "{app}\EduPrinterService.exe"
Name: "{group}\Uninstall Edu Printer System"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Edu Printer System"; Filename: "{app}\EduPrinterService.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EduPrinterService.exe"; Parameters: "install"; StatusMsg: "Installing Windows service..."; Flags: runhidden waituntilterminated
Filename: "net"; Parameters: "start EduPrinterService"; StatusMsg: "Starting service..."; Flags: runhidden waituntilterminated

[UninstallRun]
Filename: "net"; Parameters: "stop EduPrinterService"; StatusMsg: "Stopping service..."; Flags: runhidden waituntilterminated
Filename: "{app}\EduPrinterService.exe"; Parameters: "remove"; StatusMsg: "Removing service..."; Flags: runhidden waituntilterminated

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Service installation and startup is handled in [Run] section
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  // Stop and remove service before uninstall
  Exec('net', 'stop EduPrinterService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{app}\EduPrinterService.exe'), 'remove', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

