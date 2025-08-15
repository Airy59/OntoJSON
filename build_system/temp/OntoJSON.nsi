
; OntoJSON NSIS Installer Script

!include "MUI2.nsh"

; General Settings
Name "OntoJSON"
OutFile "C:\OntoJSON\build_system\dist\OntoJSON-1.0.0-Setup.exe"
InstallDir "$PROGRAMFILES64\OntoJSON"
InstallDirRegKey HKLM "Software\OntoJSON" "Install_Dir"
RequestExecutionLevel admin

; UI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "C:\OntoJSON\Resources\ORW_big.png"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${NSISDIR}\Docs\Modern UI\License.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  
  ; Copy files
  File "C:\OntoJSON\build_system\dist\OntoJSON.exe"
  
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\OntoJSON"
  CreateShortcut "$SMPROGRAMS\OntoJSON\OntoJSON.lnk" "$INSTDIR\OntoJSON.exe"
  CreateShortcut "$SMPROGRAMS\OntoJSON\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\OntoJSON.lnk" "$INSTDIR\OntoJSON.exe"
  
  ; Write registry keys
  WriteRegStr HKLM "Software\OntoJSON" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OntoJSON" "DisplayName" "OntoJSON"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OntoJSON" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OntoJSON" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OntoJSON" "NoRepair" 1
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; Uninstaller Section
Section "Uninstall"
  Delete "$INSTDIR\OntoJSON.exe"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$DESKTOP\OntoJSON.lnk"
  
  RMDir /r "$SMPROGRAMS\OntoJSON"
  RMDir "$INSTDIR"
  
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OntoJSON"
  DeleteRegKey HKLM "Software\OntoJSON"
SectionEnd
