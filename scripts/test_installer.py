"""Exercise the real installer in an isolated folder; refuse existing installs.

Temporarily creates the product's HKCU uninstall entry and Start menu shortcut.
It refuses to replace an existing registration/shortcut and removes test entries
through the real uninstaller. Application preferences are only hashed, never edited.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import time
import uuid
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL_KEY = r'Software\Biuret\PrayerPalInstaller'
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\BiuretPrayerPal'


def registry_snapshot(key):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as handle:
            values, children = [], {}
            for index in range(winreg.QueryInfoKey(handle)[1]):
                name, value, kind = winreg.EnumValue(handle, index)
                values.append((name, repr(value), kind))
            for index in range(winreg.QueryInfoKey(handle)[0]):
                name = winreg.EnumKey(handle, index)
                children[name] = registry_snapshot(key + '\\' + name)
            return {'values': values, 'children': children}
    except FileNotFoundError:
        return None


def known_folder(identifier):
    buffer = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, identifier, None, 0, buffer):
        raise OSError('Could not resolve current-user shortcut folder.')
    return Path(buffer.value)


def invoke(executable, *arguments, destination=None, uninstall=False):
    command = subprocess.list2cmdline([str(executable), *arguments])
    if destination:
        # NSIS consumes the remaining raw command line after /D= or _?=.
        # This is CreateProcess text, not a shell command; no shell is invoked.
        command += (' _?=' if uninstall else ' /D=') + str(destination)
    return subprocess.run(command, cwd=ROOT, timeout=60, check=False).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer', type=Path, required=True)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--validation-namespace', action='store_true',
                        help='Requires an installer compiled with --validation-namespace')
    arguments = parser.parse_args()
    global INSTALL_KEY, UNINSTALL_KEY
    shortcut_name = 'Biuret PrayerPal'
    if arguments.validation_namespace:
        INSTALL_KEY += 'Validation101'
        UNINSTALL_KEY += 'Validation101'
        shortcut_name += ' validation 1.0.1'
    installer, payload = arguments.installer.resolve(), arguments.payload.resolve()
    if arguments.validation_namespace:
        metadata = installer.parent / 'V1.0.1-INSTALLER_BUILD_INFO.json'
        details = json.loads(metadata.read_text(encoding='utf-8'))
        installer_hash = hashlib.sha256(installer.read_bytes()).hexdigest()
        payload_hash = hashlib.sha256(payload.read_bytes()).hexdigest()
        if (details.get('validation_namespace') is not True
                or details.get('sha256') != installer_hash
                or details.get('payload_sha256') != payload_hash):
            raise RuntimeError('Validation installer identity/hash check failed; test refused.')
    shortcuts = [known_folder(2) / (shortcut_name + '.lnk'),
                 known_folder(0x10) / (shortcut_name + '.lnk')]
    if any(registry_snapshot(key) is not None for key in (INSTALL_KEY, UNINSTALL_KEY)):
        raise RuntimeError('Existing installation registration preserved; test refused.')
    if any(path.exists() for path in shortcuts):
        raise RuntimeError('Existing product shortcut preserved; test refused.')
    preferences_before = registry_snapshot(r'Software\MyApps\PrayerReminder')
    production_keys = (r'Software\Biuret\PrayerPalInstaller',
                       r'Software\Microsoft\Windows\CurrentVersion\Uninstall\BiuretPrayerPal',
                       r'Software\Microsoft\Windows\CurrentVersion\Run')
    production_before = [registry_snapshot(key) for key in production_keys]
    production_shortcuts = [known_folder(folder) / 'Biuret PrayerPal.lnk' for folder in (2, 0x10)]
    shortcuts_before = [path.read_bytes() if path.exists() else None
                        for path in production_shortcuts]
    run_key = r'Software\Microsoft\Windows\CurrentVersion\Run'
    run_value = 'BiuretPrayerPalValidation101'

    def startup_value(command=None, *, remove=False):
        # This helper is exclusively for the test-only value; never production.
        assert arguments.validation_namespace
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, run_key, 0,
                                winreg.KEY_READ | winreg.KEY_SET_VALUE) as handle:
            if command is not None:
                winreg.SetValueEx(handle, run_value, 0, winreg.REG_SZ, command)
            try:
                value = winreg.QueryValueEx(handle, run_value)[0]
                if remove:
                    winreg.DeleteValue(handle, run_value)
                return value
            except FileNotFoundError:
                return None

    if arguments.validation_namespace and startup_value() is not None:
        raise RuntimeError('Existing validation startup value preserved; test refused.')
    root = (ROOT / 'artifacts' / ('installer-lifecycle-' + uuid.uuid4().hex)).resolve()
    assert root.is_relative_to((ROOT / 'artifacts').resolve())
    root.mkdir()
    target = root / 'تثبيت PrayerPal' / 'app'
    unowned = root / 'unowned'
    unowned.mkdir()
    sentinel = unowned / 'keep.txt'
    sentinel.write_text('preserve unrelated data', encoding='utf-8')
    outcomes = {}
    installed = target / 'BiuretPrayerPal.exe'
    uninstall = target / 'Uninstall.exe'
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    second_target = root / 'startup-ownership'
    try:
        assert invoke(installer, '/S', destination=unowned) == 2
        assert sentinel.read_text() == 'preserve unrelated data'
        assert registry_snapshot(INSTALL_KEY) is None
        outcomes['unowned_folder_refused'] = True
        assert invoke(installer, '/S', destination=target) == 0
        assert hashlib.sha256(installed.read_bytes()).hexdigest() == digest
        assert uninstall.is_file() and shortcuts[0].is_file()
        assert registry_snapshot(UNINSTALL_KEY) is not None
        outcomes['install_unicode_path_registration_shortcut'] = True
        user_file = target / 'user-file.keep'
        user_file.write_text('user data must survive', encoding='utf-8')
        assert invoke(installer, '/S', destination=target) == 0
        assert user_file.read_text() == 'user data must survive'
        outcomes['reinstall_preserves_extra_files'] = True
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
                                       ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                       ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(installed), 0x80000000, 0, None, 3, 0, None)
        assert handle != ctypes.c_void_p(-1).value
        try:
            assert invoke(installer, '/S', destination=target) == 2
            assert invoke(uninstall, '/S', destination=target, uninstall=True) == 2
        finally:
            kernel.CloseHandle(handle)
        assert hashlib.sha256(installed.read_bytes()).hexdigest() == digest
        outcomes['locked_payload_blocks_install_and_uninstall'] = True
        report = root / 'installed-app-smoke.json'
        environment = dict(os.environ, QT_QPA_PLATFORM='windows', QT_MEDIA_BACKEND='windows')
        for variable in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH',
                         'QT_QPA_PLATFORM_PLUGIN_PATH'):
            environment.pop(variable, None)
        result = subprocess.run([str(installed), '--packaging-smoke-test', str(report)],
                                cwd=root, env=environment, timeout=60, check=False)
        assert result.returncode == 0 and json.loads(report.read_text())['passed']
        outcomes['installed_app_gui_audio_smoke'] = True
        if arguments.validation_namespace:
            startup_value(f'"{installed}" --startup')
        assert invoke(uninstall, '/S') == 0
        deadline = time.monotonic() + 30
        while installed.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not installed.exists()
        assert not any(path.exists() for path in shortcuts)
        assert registry_snapshot(INSTALL_KEY) is None
        assert registry_snapshot(UNINSTALL_KEY) is None
        assert user_file.read_text() == 'user data must survive'
        if arguments.validation_namespace:
            assert startup_value() is None
            assert invoke(installer, '/S', destination=second_target) == 0
            startup_value('"C:\\Another App\\PrayerPal.exe" --startup')
            second_uninstall = second_target / 'Uninstall.exe'
            assert invoke(second_uninstall, '/S', destination=second_target, uninstall=True) == 0
            assert startup_value() == '"C:\\Another App\\PrayerPal.exe" --startup'
            startup_value(remove=True)
            outcomes['uninstall_startup_exact_owner_removed_other_owner_preserved'] = True
        assert registry_snapshot(r'Software\MyApps\PrayerReminder') == preferences_before
        if arguments.validation_namespace:
            assert [registry_snapshot(key) for key in production_keys] == production_before
            assert [path.read_bytes() if path.exists() else None
                    for path in production_shortcuts] == shortcuts_before
            outcomes['production_install_startup_shortcuts_unchanged'] = True
        outcomes['uninstall_preserves_user_files_and_preferences'] = True
        result = {'passed': True, 'validation_namespace': arguments.validation_namespace,
                  'checks': outcomes, 'installer_sha256':
                  hashlib.sha256(installer.read_bytes()).hexdigest(), 'payload_sha256': digest}
        name = ('installer-lifecycle-V1.0.1-validation.json' if arguments.validation_namespace
                else 'installer-lifecycle.json')
        (ROOT / 'artifacts' / name).write_text(
            json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))
        return 0
    finally:
        # On failure the evidence stays available. Never recursively erase a target.
        if installed.exists() and uninstall.exists():
            invoke(uninstall, '/S')
        if arguments.validation_namespace:
            other_uninstall = second_target / 'Uninstall.exe'
            if (second_target / 'BiuretPrayerPal.exe').exists() and other_uninstall.exists():
                invoke(other_uninstall, '/S', destination=second_target, uninstall=True)
            startup_value(remove=True)


if __name__ == '__main__':
    raise SystemExit(main())
