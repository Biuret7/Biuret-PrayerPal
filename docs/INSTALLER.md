# Windows installer — V1.0.0

Download **BiuretPrayerPal-V1.0.0-Windows-x64.exe** from the
[release](https://github.com/Biuret7/Biuret-PrayerPal/releases/tag/V1.0.0).
This primary download now runs the installer. Its existing URL is retained.

1. Run the wizard and select Arabic or English.
2. Keep the default current-user application folder, or select an empty folder.
3. Optionally enable a desktop shortcut. A Start menu shortcut is always added.
4. Open Biuret PrayerPal from Start, configure your city/time zone, then test reminders.

No Python, administrator elevation, or additional audio download is required.
The installer and application are unsigned. It requires x64 Windows 10 or later;
the local verification does not certify every Windows build, device or codec.

التنزيل الأساسي أصبح معالج تثبيت. بعد تثبيته افتح البرنامج من قائمة Start.
لتجربة الأذان: **الإعدادات ← الصوت ← أذان عمر هشام العربي (مرفق) ← اختبار التذكير**،
مع إلغاء الكتم وضبط مستوى الصوت فوق الصفر.

## Reinstall and uninstall

Exit the app from its tray icon before reinstalling or removing it. Reinstalling
uses the registered folder; to move an existing installation, uninstall it first.
Remove it through Windows **Settings → Apps → Installed apps → Biuret PrayerPal**.
The uninstaller removes explicitly installed files and shortcuts. Personal
preferences under `MyApps/PrayerReminder`, custom audio, and unrelated files remain.
It does not recursively erase the installation directory.

The release distributes the Windows installer. The earlier Portable download and
its checksum files have been removed from the release.

## Build the installer

The application payload is built with PyInstaller; NSIS wraps that verified payload
in the installer. See [BUILD_WINDOWS.md](BUILD_WINDOWS.md) for the first step.

Use the official [NSIS 3.13 ZIP](https://sourceforge.net/projects/nsis/files/NSIS%203/3.13/nsis-3.13.zip/download).
Its published SHA-256 is:

```text
ba63dffc4410ee89193e1cb5a41989991bd77c61068da17e3156d136b7b0b3d8
```

Save it as `artifacts/installer-tools/nsis-3.13.zip` and verify the hash before
extracting. No globally installed compiler is necessary.

```powershell
Get-FileHash artifacts/installer-tools/nsis-3.13.zip -Algorithm SHA256
Expand-Archive artifacts/installer-tools/nsis-3.13.zip artifacts/installer-tools
python -m pip install -r requirements-build.txt
python build.py
python build_installer.py --app-exe release/BiuretPrayerPal.exe
```

For an installed compiler, pass `--makensis` with its full `makensis.exe` path.
`build_installer.bat` is the double-click wrapper after dependencies and the payload
are prepared. The output is `release/BiuretPrayerPal-V1.0.0-Setup-Windows-x64.exe`,
its SHA-256 file and `INSTALLER_BUILD_INFO.json`. The release publishes these same
installer bytes using the existing primary download filename without `-Setup`.

The build checks payload version, x64 machine type, GUI subsystem, icon/resources,
plugins and bundled audio, then executes the actual frozen payload with isolated
settings and muted WAV/MP3 playback. NSIS compilation treats warnings as errors,
uses explicit UTF-8 input, and retains logs under `artifacts/installer/`.
Generated staging is temporary; existing release output is replaced only after success.

The installer uses Unicode NSIS 3.13, Modern UI 2, Arabic/English, current-user HKCU
registration and zlib compression. `packaging/NSIS_LICENSE.txt` is copied unchanged
from the official compiler package and installed beside the application.

## Lifecycle validation

On a Windows account without an existing PrayerPal installer registration/shortcut:

```powershell
python scripts/test_installer.py --installer release/BiuretPrayerPal-V1.0.0-Setup-Windows-x64.exe --payload release/BiuretPrayerPal.exe
```

This real integration test temporarily registers a test installation and creates its
Start shortcut, then uses the actual uninstaller to clean those entries. It refuses
an existing product installation/shortcut. It covers a Unicode path with spaces,
reinstallation, locked executable refusal, installed GUI/audio playback, preference
preservation and survival of unrelated files. The report stays in
`artifacts/installer-lifecycle.json`; test evidence stays under `artifacts/`.

Clean-machine certification, signing, interactive wizard/Narrator and broad hardware
testing remain unverified. The original V1.0.0 Git tag remains the application source
checkpoint. Installer scripts and current documentation are in `main` and the
`Biuret-PrayerPal-V1.0.0-installer-source.zip` release attachment.
