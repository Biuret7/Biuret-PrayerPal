> To create the installable distribution, continue with [INSTALLER.md](INSTALLER.md)
> after building the application payload below. GitHub’s primary EXE download is now the installer.

# Build Biuret PrayerPal for Windows

Version 1.0.1 is distributed as a Windows installer. Building remains local; these scripts never upload to GitHub.

These are the complete build inputs for the existing **PySide6 / Qt 6** application.
The source does not use PyQt6, so the spec deliberately excludes PyQt6/PyQt5 rather
than mixing Qt bindings. No binding migration is needed to create the executable.

## One-click build

Double-click `build_exe.bat`. It creates a dedicated `.venv-build`, installs the
pinned `requirements-build.txt`, then runs `build.py` with that same interpreter.
The build console is visible; the finished application has **no console window**.
The batch file stops on installation/build failure and preserves the failure exit code.

## Exact PowerShell commands

Run on Windows with 64-bit Python. The tested interpreter is Python 3.14.6 x64.

```powershell
git clone https://github.com/Biuret7/Biuret-PrayerPal.git
Set-Location Biuret-PrayerPal
py -3.14 -m venv .venv-build
& .\.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
& .\.venv-build\Scripts\python.exe build.py
& .\release\BiuretPrayerPal-V1.0.1-Windows-x64.exe
```

Activation is optional; using the venv executable explicitly avoids installing into
one interpreter and building with another. With an existing compatible environment:

```powershell
python -m pip install -r requirements-build.txt
python build.py
```

The output is `release/BiuretPrayerPal-V1.0.1-Windows-x64.exe`, with its SHA-256 checksum,
`V1.0.1-BUILD_INFO.json` and notices. It is the one-file application payload,
not an MSI/setup wizard. PyInstaller collects the interpreter and runtime dependencies.

## Build options and safe cleanup

```powershell
# Preserve temporary staging files when diagnosing a failure:
& .\.venv-build\Scripts\python.exe build.py --keep-work

# Explicitly bypass execution checks in a non-interactive build environment:
& .\.venv-build\Scripts\python.exe build.py --skip-smoke
```

The normal build removes old, owned `build/` and `dist/` directories before building,
then removes them after success or failure. Only these exact project-local paths
are allowed. An ownership marker, resolved-path checks, and a link/junction/reparse
scan protect unrelated files. A nonempty unmarked directory is refused and preserved.
Inspect/move such a directory yourself before retrying; do not disable the checks.
A Windows byte-range lock prevents concurrent builds from deleting each other's work.

`release/` and `artifacts/build/` are not cleaned. An existing successful executable
is replaced atomically only after its new candidate passes validation. Build logs and
smoke JSON reports remain under `artifacts/build/`. Timeouts terminate only the known
build command's process tree. `--skip-smoke` is recorded as untested in build metadata.

## What the bundle includes

- A seven-resolution `icon.ico` (16 through 256 pixels), embedded into the EXE and
  collected as a read-only runtime asset for the app window/tray icon.
- `assets/sounds/chime.wav`, the generated, non-speech application chime. All files
  placed under `assets/` are collected, preserving their relative paths. Only place
  public application assets and redistributable recordings there.
- Styles and default preferences compiled from `theme.py`, `preferences.py`, and
  `core.py`. There are currently no external QSS files or database seed files.
- tzdata's zoneinfo data and dependency/license metadata. This keeps IANA timezone
  lookup working on a Windows PC without a Python installation.
- PySide6/shiboken6 modules, Qt DLL dependencies, Windows platform plugins, icon/image
  plugins, the native Windows multimedia backend, and the installed FFmpeg backend
  and its private DLLs. Standard PyInstaller Qt hooks resolve transitive dependencies;
  the spec also explicitly collects the relevant plugin groups and hidden imports.

The included `assets/sounds/adhan-omar-hisham-al-arabi.mp3` is bundled too.
Select **أذان عمر هشام العربي (مرفق)** in Sound settings, unmute, and press
Test Reminder. See [recording attribution](../assets/sounds/README.md).

Other personal Adhan/Azkar files referenced by saved preferences are **not automatically
copied into a public build**. The app still lets recipients choose their own files.
User QSettings values remain under `MyApps/PrayerReminder` in the Windows user profile.
The bundled chime and icon are read via `resources.resource_path()`; their source
fallbacks remain available. Do not save mutable preferences or a live database into
the one-file extraction directory. [PyInstaller's resource notes](https://pyinstaller.org/en/stable/spec-files.html#adding-files-to-the-bundle)
explain why changes there do not survive application exit.

The spec uses `console=False` (the equivalent of `--windowed/--noconsole`), sets
`icon=...`, and disables UPX. Windows version metadata identifies version 1.0.1.
The app runs without administrator elevation. [Spec-file documentation](https://pyinstaller.org/en/stable/spec-files.html)
describes how `Analysis`, `PYZ`, and `EXE` replace corresponding command-line options.

## DLL issue diagnosed during verification

The first compiled candidate failed its frozen QtCore import. Binary analysis showed
that an unrelated Poppler directory on the host PATH supplied `icuuc.dll` with
version-suffixed exports, while Qt required Windows' unversioned ICU exports. The
spec now sanitizes DLL search PATH to Windows/System32, Windows, and the Python
locations before dependency analysis. Windows system libraries remain supplied by
Windows; they are not copied from random toolchains. A post-build check rejects an
incompatible collected ICU DLL. No PyQt runtime was included.

Qt's native Windows multimedia backend remains the default established by the app.
It was verified with the bundled WAV and MP3 and muted output; external codec support still
depends on Windows and the selected file. Qt marks this native backend deprecated
within Qt 6, so review that choice before a future Qt 7 migration.
[Qt multimedia backend notes](https://doc.qt.io/qt-6/qtmultimedia-index.html).

## Verification performed by build.py

1. Checks required inputs and installed build packages.
2. Compiles a one-file Windows GUI executable using the supplied spec.
3. Inspects the PE GUI subsystem, icon/version resources, embedded Qt plugins,
   multimedia library, chime, icon, timezone data, and absence of PyQt bindings.
4. Starts the actual frozen EXE from a separate working directory with Python/Qt
   environment overrides removed and a Windows-only PATH. Checks the visible window,
   its icon, unsaved settings preview, bundled timezone calculations, and native
   WAV playback through EndOfMedia and bundled Adhan MP3 playback with output muted. Test settings use a temporary
   INI file, not the user's registry settings. An eight-second in-app watchdog and
   an outer process deadline report failure instead of false success.
5. Copies the candidate and checksum to the local release folder, then cleans staging files.
   It never uploads to GitHub. Versioned outputs preserve previous release files.

The ordinary source suite also covers cleanup refusal, directory containment, and
concurrent build locking. Run it with `python prayerpal.py --self-test`; Qt tests are
separate under `tests/gui/`. A frozen `--self-test` request returns 2 because source
tests are intentionally not shipped. The build uses `--packaging-smoke-test REPORT`
instead.

## Distribution checks

The generated EXE is unsigned. Authenticode signing, an installer, clean-PC testing
without Python, and hardware/codec coverage remain separate distribution checks.
The local NSIS installer workflow is documented in INSTALLER.md.
Keep applicable license notices and meet the bundled dependencies' redistribution
obligations; packaging itself does not grant rights to third-party recordings or
remove license requirements. No certificate or publisher identity was invented.

You can change the product icon by replacing `icon.ico` with a valid multi-resolution
ICO and rebuilding. To add static QSS/images/default seed files later, place them in
`assets/` and read them with `resource_path('assets/...')`. Application code must
actually load those assets; bundling alone does not activate a new theme or database.

## Complete build inputs

The maintained files are [build.py](../build.py), [BiuretPrayerPal.spec](../BiuretPrayerPal.spec),
[build_exe.bat](../build_exe.bat), and [requirements-build.txt](../requirements-build.txt).
Close any running release executable before replacing it. Windows may also temporarily
lock a new executable while scanning it; a failed publication preserves the prior output.

For GitHub V1.0.0 the validated output is renamed to
`BiuretPrayerPal-V1.0.0-Windows-x64.exe`, with a matching SHA-256 file.
