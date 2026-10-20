# V1.0.0 verification — 2026-10-20

Verified on Windows x64, Python 3.14.6 and PySide6/Qt 6.12.0.

- `python prayerpal.py --self-test`: 34 tests passed.
- `python -m unittest discover -s tests/gui -v`: 21 native Windows Qt/process tests passed.
- Source PEP 8 checks and compilation passed. Native UI screenshots generated with isolated settings.
- Actual frozen Windows GUI executable: icon/assets/timezones/settings preview/window visibility passed.
- Muted native playback: bundled WAV reached EndOfMedia; bundled Adhan MP3 position advanced.
- EXE SHA-256: `0b85c190a5d79eff27a4643831efd94ff1d0034461b820361ee4f218f2901338`.

Windows refused replacement of a prior local `release/BiuretPrayerPal.exe`.
The validated candidate was instead atomically copied to the versioned release filename;
the old file was preserved. The frozen smoke check passed before publication.

The executable is unsigned. Clean-PC installation without Python, signing, Narrator,
multiple physical monitors and broader audio-device/codec coverage remain unverified.

## Installer packaging update — 2026-10-20

The primary EXE URL now serves the NSIS installer; the original application
payload is unchanged and retained under the Portable filename.

- NSIS 3.13 ZIP SHA-256 matched the officially published checksum.
- Compiler warnings treated as errors; explicit UTF-8, Arabic/English tables.
- Final installer PE GUI subsystem and asInvoker manifest verified.
- Real silent install in a Unicode path with spaces, registry registration and Start shortcut passed.
- Reinstall, unowned-folder refusal and locked-file refusal passed.
- Installed application GUI, bundled WAV and Adhan MP3 smoke checks passed.
- Uninstall removed its records/shortcuts and retained unrelated files and preferences.
- Installer SHA-256: `51857cdfb90eb4581cd9675b672f50710313094bfe1c170b5e1e1d22433d120e`.

The wizard's interactive flow, desktop option, Narrator, signing and a clean
Windows machine without development tools remain unverified.
