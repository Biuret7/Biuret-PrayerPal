# -*- mode: python ; coding: utf-8 -*-
"""One-file, windowed Windows build for the existing PySide6 application."""
from pathlib import Path
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, copy_metadata
from PyInstaller.utils.hooks.qt import pyside6_library_info
import PySide6

ROOT = Path(SPECPATH).resolve()
qt_root = Path(PySide6.__file__).resolve().parent
# Prefer Windows' unversioned ICU and exclude unrelated toolchains from DLL
# discovery. A Poppler ICU on PATH has incompatible suffixed exports for Qt.
windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
os.environ['PATH'] = os.pathsep.join(map(str, (
    windows / 'System32', windows, Path(sys.executable).parent, Path(sys.base_prefix),
)))

# datas is the spec-file equivalent of --add-data. Mutable user settings are
# deliberately excluded: QSettings keeps them in the user's Windows profile.
datas = [
    (str(ROOT / 'icon.ico'), '.'),
    (str(ROOT / 'assets'), 'assets'),
    (str(ROOT / 'packaging/THIRD_PARTY_NOTICES.txt'), '.'),
]
datas += collect_data_files('tzdata')
for distribution in ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'tzdata'):
    datas += copy_metadata(distribution)
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.is_file():
    datas.append((str(python_license), 'licenses/python'))
datas += collect_data_files('PySide6', includes=['**/LICENSE*', '**/COPYING*', '**/licenses/**'])

# Standard PyInstaller Qt hooks resolve Qt DLL dependencies. Explicit plugin
# collections also include the native Windows audio backend and the optional
# FFmpeg backend. Do not collect all of PySide6 (that pulls in WebEngine, etc.).
binaries = []
for plugin_type in ('platforms', 'multimedia', 'imageformats', 'styles'):
    binaries += pyside6_library_info.collect_plugins(plugin_type)
for folder in {qt_root, qt_root / 'bin', Path(pyside6_library_info.location['BinariesPath'])}:
    for pattern in ('avcodec-*.dll', 'avformat-*.dll', 'avutil-*.dll',
                    'swresample-*.dll', 'swscale-*.dll', 'avfilter-*.dll', 'avdevice-*.dll'):
        binaries += [(str(path), 'PySide6') for path in folder.glob(pattern)]

analysis = Analysis(
    [str(ROOT / 'prayerpal.py')],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'PySide6.QtMultimedia', 'shiboken6', 'tzdata',
    ],
    hookspath=[],
    runtime_hooks=[str(ROOT / 'packaging/runtime_hook.py')],
    excludes=[
        'PyQt6', 'PyQt5', 'PySide2',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
    ],
    noarchive=False,
)
for required in ('qwindows.dll', 'windowsmediaplugin.dll', 'Qt6Multimedia.dll'):
    if not any(Path(entry[0]).name.lower() == required.lower() for entry in analysis.binaries):
        raise RuntimeError(f'Required Qt runtime binary was not collected: {required}')

pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, analysis.binaries, analysis.datas, [],
    name='BiuretPrayerPal',
    icon=str(ROOT / 'icon.ico'),
    version=str(ROOT / 'packaging/version_info.txt'),
    console=False,
    debug=False,
    strip=False,
    upx=False,
    disable_windowed_traceback=False,
    uac_admin=False,
    runtime_tmpdir=None,
)
