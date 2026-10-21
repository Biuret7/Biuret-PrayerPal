; -*- coding: utf-8 -*-
; Per-user installer. No elevation, downloads, autorun, or settings deletion.
Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"

!ifndef APP_VERSION
  !error "Use build_installer.py to supply validated build inputs."
!endif
; The validation build changes only OS registration identity, never install logic.
; It stays under artifacts/ and must never be distributed as the application.
!ifdef VALIDATION_BUILD
  !define PRODUCT_ID "Biuret.PrayerPal.Validation101"
  !define INSTALL_KEY "Software\Biuret\PrayerPalInstallerValidation101"
  !define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\BiuretPrayerPalValidation101"
  !define SHORTCUT_NAME "Biuret PrayerPal validation 1.0.1"
  !define STARTUP_VALUE "BiuretPrayerPalValidation101"
  !define SETUP_MUTEX "Local\BiuretPrayerPalSetupValidation101"
!else
  !define PRODUCT_ID "Biuret.PrayerPal.Windows"
  !define INSTALL_KEY "Software\Biuret\PrayerPalInstaller"
  !define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\BiuretPrayerPal"
  !define SHORTCUT_NAME "Biuret PrayerPal"
  !define STARTUP_VALUE "BiuretPrayerPal"
  !define SETUP_MUTEX "Local\BiuretPrayerPalSetup"
!endif

Name "Biuret PrayerPal"
OutFile "${OUTPUT_EXE}"
InstallDir "$LOCALAPPDATA\Programs\${SHORTCUT_NAME}"
InstallDirRegKey HKCU "${INSTALL_KEY}" "InstallDir"
RequestExecutionLevel user
ManifestDPIAware true
SetCompressor /SOLID zlib
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "Biuret PrayerPal Setup"
VIAddVersionKey /LANG=1033 "FileDescription" "Biuret PrayerPal Installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "CompanyName" "Biuret"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Third-party components retain their respective copyrights."

!define MUI_ICON "${PROJECT_ROOT}\icon.ico"
!define MUI_UNICON "${PROJECT_ROOT}\icon.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Biuret PrayerPal ${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "$(WelcomeText)"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\BiuretPrayerPal.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "Arabic"
!insertmacro MUI_LANGUAGE "English"

LangString WelcomeText ${LANG_ARABIC} "رفيقك اليومي للصلاة والذكر.$\r$\n$\r$\nيثبّت البرنامج لحسابك الحالي مع اختصارات وإزالة تثبيت. الأذان بصوت عمر هشام العربي مرفق ويعمل دون تنزيل ملف آخر.$\r$\n$\r$\nأغلق البرنامج من أيقونة شريط النظام قبل إعادة التثبيت. تبقى إعداداتك محفوظة."
LangString WelcomeText ${LANG_ENGLISH} "Your daily companion for prayer and remembrance.$\r$\n$\r$\nInstalls for your current account with shortcuts and an uninstaller. Includes Adhan by Omar Hisham Al Arabi; no extra download is needed.$\r$\n$\r$\nExit the app from its tray icon before reinstalling. Your preferences are preserved."
LangString CoreName ${LANG_ARABIC} "البرنامج والأذان المرفق (مطلوب)"
LangString CoreName ${LANG_ENGLISH} "Application and bundled Adhan (required)"
LangString DesktopName ${LANG_ARABIC} "اختصار سطح المكتب"
LangString DesktopName ${LANG_ENGLISH} "Desktop shortcut"
LangString CloseApp ${LANG_ARABIC} "أغلق Biuret PrayerPal من أيقونة شريط النظام، ثم أعد المحاولة. لم تُحذف إعداداتك."
LangString CloseApp ${LANG_ENGLISH} "Exit Biuret PrayerPal from its tray icon, then try again. Your preferences have not been deleted."
LangString FolderError ${LANG_ARABIC} "اختر مجلداً فارغاً خاصاً بالبرنامج، أو مجلد تثبيت Biuret PrayerPal السابق. لا يمكن استخدام هذا المجلد."
LangString FolderError ${LANG_ENGLISH} "Choose an empty application folder or the previous Biuret PrayerPal installation. This folder cannot be used."

Var SetupMutex
Var ExistingInstall

!macro InitInstaller PREFIX
Function ${PREFIX}.onInit
  SetShellVarContext current
  SetRegView 64
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "This installer requires 64-bit Windows."
    SetErrorLevel 2
    Quit
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "Windows 10 or later is required."
    SetErrorLevel 2
    Quit
  ${EndIf}
  System::Call 'kernel32::CreateMutexW(p 0, i 0, w "${SETUP_MUTEX}") p .r0 ?e'
  Pop $1
  StrCpy $SetupMutex $0
  ${If} $0 P= 0
    SetErrorLevel 2
    Quit
  ${EndIf}
  ${If} $1 == 183
    SetErrorLevel 2
    Quit
  ${EndIf}
  !if "${PREFIX}" == ""
    ${IfNot} ${Silent}
      !insertmacro MUI_LANGDLL_DISPLAY
    ${EndIf}
    ReadRegStr $ExistingInstall HKCU "${INSTALL_KEY}" "InstallDir"
  !endif
FunctionEnd
!macroend
!insertmacro InitInstaller ""
!insertmacro InitInstaller "un"

; Require an empty target or our explicit marker. Never adopt unrelated files.
Function ValidateTarget
  ${If} $ExistingInstall != ""
  ${AndIf} $ExistingInstall != $INSTDIR
    Goto target_error
  ${EndIf}
  IfFileExists "$INSTDIR\BiuretPrayerPal.install.ini" owned_target
  FindFirst $0 $1 "$INSTDIR\*"
  target_loop:
    ${If} $1 == ""
      FindClose $0
      Return
    ${EndIf}
    ${If} $1 != "."
    ${AndIf} $1 != ".."
      FindClose $0
      Goto target_error
    ${EndIf}
    FindNext $0 $1
    Goto target_loop
  owned_target:
    ReadINIStr $0 "$INSTDIR\BiuretPrayerPal.install.ini" "Install" "Product"
    StrCmp $0 "${PRODUCT_ID}" target_ok target_error
  target_error:
    IfSilent +2
      MessageBox MB_OK|MB_ICONSTOP "$(FolderError)"
    SetErrorLevel 2
    Abort
  target_ok:
FunctionEnd

Function .onVerifyInstDir
  Call ValidateTarget
FunctionEnd

; An exclusive write-open detects a running/locked EXE without terminating it.
!macro CheckUnlocked PREFIX
Function ${PREFIX}CheckUnlocked
  IfFileExists "$INSTDIR\BiuretPrayerPal.exe" 0 unlocked
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\BiuretPrayerPal.exe", i 0x40000000, i 0, p 0, i 3, i 0, p 0) p .r0'
  ${If} $0 P= -1
    IfSilent +2
      MessageBox MB_OK|MB_ICONSTOP "$(CloseApp)"
    SetErrorLevel 2
    Abort
  ${EndIf}
  System::Call 'kernel32::CloseHandle(p r0)'
  unlocked:
FunctionEnd
!macroend
!insertmacro CheckUnlocked ""
!insertmacro CheckUnlocked "un."

Section "$(CoreName)" MainSection
  SectionIn RO
  Call ValidateTarget
  Call CheckUnlocked
  SetErrorLevel 0
  SetOutPath "$INSTDIR"
  SetOverwrite on
  ; Stage first; retain the previous executable if promotion fails.
  ClearErrors
  File /oname=BiuretPrayerPal.exe.new "${PAYLOAD_EXE}"
  IfErrors install_failed
  IfFileExists "$INSTDIR\BiuretPrayerPal.exe.previous" install_failed
  IfFileExists "$INSTDIR\BiuretPrayerPal.exe" 0 promote
    Rename "$INSTDIR\BiuretPrayerPal.exe" "$INSTDIR\BiuretPrayerPal.exe.previous"
    IfErrors install_failed
  promote:
    ClearErrors
    Rename "$INSTDIR\BiuretPrayerPal.exe.new" "$INSTDIR\BiuretPrayerPal.exe"
    IfErrors rollback
    File /oname=icon.ico "${PROJECT_ROOT}\icon.ico"
    File /oname=THIRD_PARTY_NOTICES.txt "${PROJECT_ROOT}\packaging\THIRD_PARTY_NOTICES.txt"
    File /oname=AUDIO_CREDITS.md "${PROJECT_ROOT}\assets\sounds\README.md"
    File /oname=NSIS_LICENSE.txt "${PROJECT_ROOT}\packaging\NSIS_LICENSE.txt"
    WriteINIStr "$INSTDIR\BiuretPrayerPal.install.ini" "Install" "Product" "${PRODUCT_ID}"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    IfErrors install_failed
    WriteRegStr HKCU "${INSTALL_KEY}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${SHORTCUT_NAME}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "Biuret"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\BiuretPrayerPal.exe,0"
    WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
    WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
    WriteRegStr HKCU "${UNINSTALL_KEY}" "URLInfoAbout" "https://github.com/Biuret7/Biuret-PrayerPal"
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
    WriteRegDWORD HKCU "${UNINSTALL_KEY}" "EstimatedSize" ${INSTALL_SIZE_KB}
    CreateShortcut "$SMPROGRAMS\${SHORTCUT_NAME}.lnk" "$INSTDIR\BiuretPrayerPal.exe"
    IfErrors install_failed
    Delete "$INSTDIR\BiuretPrayerPal.exe.previous"
    Goto install_done
  rollback:
    Rename "$INSTDIR\BiuretPrayerPal.exe.previous" "$INSTDIR\BiuretPrayerPal.exe"
  install_failed:
    Delete "$INSTDIR\BiuretPrayerPal.exe.new"
    IfSilent +2
      MessageBox MB_OK|MB_ICONSTOP "Installation could not finish. Your preferences were preserved."
    SetErrorLevel 2
    Abort
  install_done:
SectionEnd

Section /o "$(DesktopName)" DesktopSection
  CreateShortcut "$DESKTOP\${SHORTCUT_NAME}.lnk" "$INSTDIR\BiuretPrayerPal.exe"
SectionEnd

Section "Uninstall"
  ReadINIStr $0 "$INSTDIR\BiuretPrayerPal.install.ini" "Install" "Product"
  ${If} $0 != "${PRODUCT_ID}"
    SetErrorLevel 2
    Abort
  ${EndIf}
  Call un.CheckUnlocked
  ; Explicit owned files only. No recursive removal or user preference deletion.
  ClearErrors
  Delete "$INSTDIR\BiuretPrayerPal.exe"
  IfErrors uninstall_failed
  Delete "$INSTDIR\icon.ico"
  Delete "$INSTDIR\THIRD_PARTY_NOTICES.txt"
  Delete "$INSTDIR\AUDIO_CREDITS.md"
  Delete "$INSTDIR\NSIS_LICENSE.txt"
  Delete "$INSTDIR\BiuretPrayerPal.exe.new"
  Delete "$INSTDIR\BiuretPrayerPal.exe.previous"
  Delete "$INSTDIR\BiuretPrayerPal.install.ini"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$SMPROGRAMS\${SHORTCUT_NAME}.lnk"
  Delete "$DESKTOP\${SHORTCUT_NAME}.lnk"
  ; Remove only a startup command owned by this exact installed executable.
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${STARTUP_VALUE}"
  ${If} $0 == '$\"$INSTDIR\BiuretPrayerPal.exe$\" --startup'
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${STARTUP_VALUE}"
  ${EndIf}
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  DeleteRegKey HKCU "${INSTALL_KEY}"
  RMDir "$INSTDIR"
  Goto uninstall_done
  uninstall_failed:
    SetErrorLevel 2
    Abort
  uninstall_done:
SectionEnd
