#define MyAppName "Application Starter Platform"
#define MyAppVersion "0.1.0"
#define MyAppExeName "ApplicationStarterPlatform.exe"

[Setup]
AppId={{E5D76C2B-4D8C-4EB5-97AD-F79B9A69A1F1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Konstantinos Andritsopoulos
AppCopyright=Copyright (c) 2026 Konstantinos Andritsopoulos
LicenseFile=LICENSE
DefaultDirName={localappdata}\Programs\ApplicationStarterPlatform
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=ApplicationStarterPlatform_Setup_0.1.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=0.1.0.0
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\ApplicationStarterPlatform\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{localappdata}\ApplicationStarterPlatform\Data"

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName}\README"; Filename: "{sys}\notepad.exe"; Parameters: """{app}\README.md"""; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName}\Configuration"; Filename: "{sys}\explorer.exe"; Parameters: """{localappdata}\ApplicationStarterPlatform\Data"""
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
function GenerateJwtSecret: String;
var
  I: Integer;
  Seed: String;
begin
  Seed :=
    GenerateUniqueName(ExpandConstant('{tmp}'), '.secret') +
    GetDateTimeString('yyyy-mm-dd hh:nn:ss.zzz', '-', ':');

  for I := 1 to 64 do
    Seed := Seed + '|' + IntToStr(Random(1000000000));

  Result := GetSHA256OfUnicodeString(Seed);
end;


procedure CreateEnvironmentFile;
var
  DataDirectory: String;
  EnvironmentFile: String;
  EnvironmentLines: TArrayOfString;
begin
  DataDirectory :=
    ExpandConstant(
      '{localappdata}\ApplicationStarterPlatform\Data'
    );

  EnvironmentFile :=
    AddBackslash(DataDirectory) + '.env';

  if FileExists(EnvironmentFile) then
  begin
    Log(
      'Existing environment file preserved: ' +
      EnvironmentFile
    );
    Exit;
  end;

  if not ForceDirectories(DataDirectory) then
    RaiseException(
      'Could not create the application data directory.'
    );

  SetArrayLength(EnvironmentLines, 45);

  EnvironmentLines[0] := '# Application identity';
  EnvironmentLines[1] :=
    'APP_APP_NAME=Application Starter Platform';
  EnvironmentLines[2] := 'APP_APP_VERSION=0.1.0';
  EnvironmentLines[3] := 'APP_ENVIRONMENT=production';
  EnvironmentLines[4] := 'APP_DEBUG=false';
  EnvironmentLines[5] := 'APP_DOCS_ENABLED=true';
  EnvironmentLines[6] := '';

  EnvironmentLines[7] := '# API server';
  EnvironmentLines[8] := 'APP_API_HOST=127.0.0.1';
  EnvironmentLines[9] := 'APP_API_PORT=8000';
  EnvironmentLines[10] :=
    'APP_OPEN_BROWSER_ON_START=true';
  EnvironmentLines[11] := '';

  EnvironmentLines[12] := '# Database';
  EnvironmentLines[13] :=
    '# SQLite path is selected automatically in the user data directory.';
  EnvironmentLines[14] := 'APP_DATABASE_ECHO=false';
  EnvironmentLines[15] := '';

  EnvironmentLines[16] := '# JWT authentication';
  EnvironmentLines[17] :=
    'APP_JWT_SECRET_KEY=' + GenerateJwtSecret;
  EnvironmentLines[18] := 'APP_JWT_ALGORITHM=HS256';
  EnvironmentLines[19] :=
    'APP_JWT_ACCESS_TOKEN_MINUTES=30';
  EnvironmentLines[20] :=
    'APP_JWT_ISSUER=application-starter-platform';
  EnvironmentLines[21] :=
    'APP_JWT_AUDIENCE=application-starter-platform-api';
  EnvironmentLines[22] := '';

  EnvironmentLines[23] := '# Account policies';
  EnvironmentLines[24] :=
    'APP_SELF_REGISTRATION_ENABLED=true';
  EnvironmentLines[25] := 'APP_PASSWORD_MIN_LENGTH=8';
  EnvironmentLines[26] := 'APP_PASSWORD_MAX_LENGTH=128';
  EnvironmentLines[27] := '';

  EnvironmentLines[28] := '# Security-token lifetimes';
  EnvironmentLines[29] :=
    'APP_EMAIL_VERIFICATION_TOKEN_MINUTES=1440';
  EnvironmentLines[30] :=
    'APP_PASSWORD_RESET_TOKEN_MINUTES=30';
  EnvironmentLines[31] := '';

  EnvironmentLines[32] := '# Frontend destinations';
  EnvironmentLines[33] :=
    'APP_PUBLIC_BASE_URL=http://127.0.0.1:8000';
  EnvironmentLines[34] := '';
  EnvironmentLines[35] := '';

  EnvironmentLines[36] := '# SMTP';
  EnvironmentLines[37] := 'APP_SMTP_ENABLED=false';
  EnvironmentLines[38] := '# APP_SMTP_HOST=smtp.example.com';
  EnvironmentLines[39] := 'APP_SMTP_PORT=587';
  EnvironmentLines[40] := '# APP_SMTP_USERNAME=';
  EnvironmentLines[41] := '# APP_SMTP_PASSWORD=';
  EnvironmentLines[42] := '# APP_SMTP_SENDER_EMAIL=';
  EnvironmentLines[43] :=
    'APP_SMTP_SENDER_NAME=Application Starter Platform';
  EnvironmentLines[44] := 'APP_SMTP_SECURITY=starttls';

  if not SaveStringsToUTF8FileWithoutBOM(
    EnvironmentFile,
    EnvironmentLines,
    False
  ) then
    RaiseException(
      'Could not create the application environment file.'
    );

  Log(
    'Environment file created: ' +
    EnvironmentFile
  );
end;


procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    CreateEnvironmentFile;
end;
