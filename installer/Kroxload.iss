; Kroxload kurulum betiği (Inno Setup 6)
; Derleme:  ISCC installer\Kroxload.iss   (önce PyInstaller: dist\Kroxload\)
#define AppName "Kroxload"
#define AppVersion "1.1.0"
#define AppExe "Kroxload.exe"

[Setup]
; AppId sabit kalmalı: yeni sürüm aynı klasöre güncelleme olarak kurulur
AppId={{77389674-C77D-4471-BB24-D593F0D5020D}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=KXR YAZILIM
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=Kroxload_Setup
SetupIconFile=..\assets\kroxload.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Kroxload Kurulumu

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ek kısayollar:"; Flags: unchecked

[Files]
Source: "..\dist\Kroxload\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Kroxload'u başlat"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Program klasöründe çalışma sırasında oluşabilecek artıklar
Type: filesandordirs; Name: "{app}"

[Code]
// Kaldırırken kullanıcıya ayar/geçmiş/günlük verisini silmek isteyip istemediği sorulur
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Veri: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Veri := ExpandConstant('{userappdata}\Kroxload');
    if DirExists(Veri) then
      if not UninstallSilent then
        if MsgBox('Ayarlar, indirme geçmişi ve günlük dosyaları da silinsin mi?' + #13#10 +
                  '(İndirdiğin müzik ve videolara dokunulmaz.)', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
          DelTree(Veri, True, True, True);
  end;
end;
