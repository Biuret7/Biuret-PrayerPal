"""Create a per-user Windows installer around a verified PrayerPal executable.

Requires NSIS 3.13 and requirements-build.txt. Does not download or install tools.
The payload must pass the real frozen GUI/audio smoke check before compilation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import build
from biuret_prayerpal.core import APP_VERSION

ROOT = Path(__file__).resolve().parent
NAME = f'BiuretPrayerPal-V{APP_VERSION}-Setup-Windows-x64.exe'


def find_compiler(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else [
        ROOT / 'artifacts/installer-tools/nsis-3.13/makensis.exe',
        Path(shutil.which('makensis.exe') or 'makensis.exe'),
        Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))
        / 'NSIS/makensis.exe',
    ]
    for candidate in candidates:
        if candidate.is_file():
            version = subprocess.check_output(
                [str(candidate.resolve()), '/VERSION'], timeout=10, text=True).strip()
            if version != 'v3.13':
                raise ValueError(f'NSIS 3.13 is required; found {version}.')
            return candidate.resolve()
    raise FileNotFoundError('NSIS 3.13 not found. Pass --makensis PATH/TO/makensis.exe.')


def validate_payload(path: Path) -> None:
    import pefile
    build.verify_executable(path)
    with pefile.PE(str(path)) as image:
        if image.FILE_HEADER.Machine != 0x8664:
            raise ValueError('The application payload must be a Windows x64 executable.')
        version = image.VS_FIXEDFILEINFO[0]
        actual = (version.FileVersionMS >> 16, version.FileVersionMS & 0xffff,
                  version.FileVersionLS >> 16)
        if actual != tuple(map(int, APP_VERSION.split('.'))):
            raise ValueError(f'Payload version {actual} does not match {APP_VERSION}.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--makensis', help='Path to the official NSIS 3.13 compiler')
    parser.add_argument('--app-exe', type=Path, help='Validated PyInstaller x64 payload')
    parser.add_argument('--validation-namespace', action='store_true',
                        help='Test-only OS identity; output stays under artifacts, never release')
    arguments = parser.parse_args()
    if os.name != 'nt':
        parser.error('Build the Windows installer on Windows.')
    preferred = ROOT / f'release/BiuretPrayerPal-V{APP_VERSION}-Windows-x64.exe'
    plain = ROOT / 'release/BiuretPrayerPal.exe'
    newest = max((path for path in (plain, preferred) if path.is_file()),
                 key=lambda path: path.stat().st_mtime, default=plain)
    payload = (arguments.app_exe or newest).resolve()
    logs = ROOT / 'artifacts/installer'
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    try:
        compiler = find_compiler(arguments.makensis)
        validate_payload(payload)
        with build.build_lock(logs / '.build.lock'):
            with tempfile.TemporaryDirectory(prefix='candidate-', dir=logs) as directory:
                staging = Path(directory).resolve()
                if not staging.is_relative_to(logs.resolve()):
                    raise ValueError('Installer staging escaped the artifact directory.')
                environment = dict(os.environ, QT_QPA_PLATFORM='windows',
                                   QT_MEDIA_BACKEND='windows')
                for name in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH',
                             'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
                    environment.pop(name, None)
                windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
                environment['PATH'] = os.pathsep.join(
                    map(str, (windows / 'System32', windows)))
                report = logs / f'{stamp}-payload-smoke.json'
                build.run([str(payload), '--packaging-smoke-test', str(report)],
                          logs / f'{stamp}-payload-smoke.log', environment,
                          timeout=60, cwd=staging)
                smoke = json.loads(report.read_text(encoding='utf-8'))
                if not smoke.get('passed') or not smoke.get('frozen'):
                    raise ValueError('Frozen application smoke check failed.')
                candidate = staging / NAME
                command = [str(compiler), '/NOCONFIG', '/WX', '/V3', '/INPUTCHARSET', 'UTF8',
                           f'/DAPP_VERSION={APP_VERSION}', f'/DPROJECT_ROOT={ROOT}',
                           f'/DPAYLOAD_EXE={payload}', f'/DOUTPUT_EXE={candidate}',
                           f'/DINSTALL_SIZE_KB={(payload.stat().st_size + 1023) // 1024 + 256}',
                           str(ROOT / 'packaging/installer.nsi')]
                if arguments.validation_namespace:
                    command.insert(-1, '/DVALIDATION_BUILD')
                print('Building installer with NSIS 3.13...', flush=True)
                build.run(command, logs / f'{stamp}-makensis.log', dict(os.environ),
                          timeout=300, cwd=ROOT)
                release = (logs / 'validation-V1.0.1' if arguments.validation_namespace
                           else ROOT / 'release')
                release.mkdir(exist_ok=True)
                if build.linked(release):
                    raise ValueError('The release directory must not be a link or junction.')
                destination = release / NAME
                with tempfile.NamedTemporaryFile(dir=release, prefix='.setup-',
                                                 delete=False) as stream:
                    publication = Path(stream.name)
                try:
                    shutil.copyfile(candidate, publication)
                    os.replace(publication, destination)
                finally:
                    publication.unlink(missing_ok=True)
                digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                destination.with_suffix('.exe.sha256').write_text(
                    f'{digest}  {NAME}\n', encoding='ascii')
                metadata = dict(version=APP_VERSION, compiler='NSIS 3.13',
                                installer=NAME, sha256=digest,
                                validation_namespace=arguments.validation_namespace,
                                bytes=destination.stat().st_size, signed=False,
                                payload_sha256=hashlib.sha256(payload.read_bytes()).hexdigest(),
                                payload_smoke_passed=True, scope='current user',
                                install_lifecycle_tested=False)
                (release / f'V{APP_VERSION}-INSTALLER_BUILD_INFO.json').write_text(
                    json.dumps(metadata, indent=2), encoding='utf-8')
                print(f'Created {destination}\nSHA-256: {digest}')
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f'Installer build failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
