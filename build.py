"""Build and verify a portable, windowed Windows executable.

Output: release/BiuretPrayerPal.exe. Run with the same Python environment that
installed requirements-build.txt. Only owned build/ and dist/ trees are cleaned.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OWNER = 'Biuret PrayerPal PyInstaller staging v1\n'
MARKER = '.prayerpal-build-owner'


@contextmanager
def build_lock(path: Path):
    """Prevent two build processes from deleting each other's staging output."""
    import msvcrt
    with path.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise OSError('Another PrayerPal build is already running.') from error
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def linked(path: Path) -> bool:
    attributes = path.lstat().st_file_attributes if os.name == 'nt' else 0
    return path.is_symlink() or bool(attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))


def checked_directory(path: Path, root: Path) -> Path:
    """Reject other products, parent traversal, links, junctions and reparse points."""
    root = root.resolve()
    if path.name not in {'build', 'dist'} or path.absolute().parent != root:
        raise OSError(f'Refusing cleanup outside the exact staging paths: {path}')
    if path.exists() or path.is_symlink():
        if linked(path) or not path.is_dir() or path.resolve().parent != root:
            raise OSError(f'Refusing cleanup of a linked/non-directory path: {path}')
        for current, directories, files in os.walk(path, followlinks=False):
            for name in directories + files:
                entry = Path(current) / name
                if linked(entry):
                    raise OSError(f'Refusing cleanup of a staging tree containing a link: {entry}')
        marker = path / MARKER
        if any(path.iterdir()) and (not marker.is_file() or marker.read_text() != OWNER):
            raise OSError(f'Refusing cleanup of unowned folder: {path}')
    return path


def clean(path: Path, root: Path = ROOT) -> None:
    path = checked_directory(path, root)
    if path.exists():
        shutil.rmtree(path)


def prepare(path: Path) -> None:
    clean(path)
    path.mkdir()
    (path / MARKER).write_text(OWNER, encoding='utf-8')


def run(command, log: Path, environment, timeout=900, cwd=ROOT) -> None:
    with log.open('w', encoding='utf-8') as output:
        with subprocess.Popen(command, cwd=cwd, env=environment, stdout=output,
                              stderr=subprocess.STDOUT) as process:
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # A one-file bootloader owns a child process. Terminate only
                # this command's known process tree, including error dialogs.
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=output, stderr=subprocess.STDOUT, timeout=10,
                               check=False)
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
                raise
    if return_code:
        raise RuntimeError(f'Command failed ({return_code}); see {log}')


def verify_executable(path: Path) -> None:
    import pefile
    from PyInstaller.archive.readers import CArchiveReader

    with pefile.PE(str(path), fast_load=False) as image:
        if image.OPTIONAL_HEADER.Subsystem != 2:
            raise RuntimeError('Executable is not a Windows GUI application (subsystem 2).')
        types = {entry.id for entry in image.DIRECTORY_ENTRY_RESOURCE.entries}
        if not {14, 16}.issubset(types):
            raise RuntimeError('Executable icon or version resource is missing.')
    archive = CArchiveReader(str(path))
    names = {name.replace('\\', '/').lower() for name in archive.toc}
    for suffix in ('icon.ico', 'assets/sounds/chime.wav',
                   'assets/sounds/adhan-omar-hisham-al-arabi.mp3', 'platforms/qwindows.dll',
                   'multimedia/windowsmediaplugin.dll', 'qt6multimedia.dll',
                   'tzdata/zoneinfo/asia/hebron'):
        if not any(name.endswith(suffix) for name in names):
            raise RuntimeError(f'Required bundled resource missing: {suffix}')
    if any('pyqt6/' in name or 'pyqt5/' in name for name in names):
        raise RuntimeError('An unintended second Qt binding was bundled.')
    for name in archive.toc:
        if Path(name).name.lower() == 'icuuc.dll':
            with pefile.PE(data=archive.extract(name)) as image:
                exports = {entry.name for entry in image.DIRECTORY_ENTRY_EXPORT.symbols}
                if b'ucnv_open' not in exports:
                    raise RuntimeError(
                        'An incompatible ICU DLL was collected from the build host.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keep-work', action='store_true',
                        help='Retain staging files for diagnosis')
    parser.add_argument('--skip-smoke', action='store_true',
                        help='Build without executing GUI/audio test')
    arguments = parser.parse_args()
    if os.name != 'nt':
        parser.error('Build the Windows EXE on Windows using a Windows Python installation.')
    components = ('PyInstaller', 'pyinstaller-hooks-contrib', 'PySide6', 'tzdata')
    try:
        versions = {name: importlib.metadata.version(name) for name in components}
    except importlib.metadata.PackageNotFoundError as error:
        print(f'Missing build dependency: {error}.')
        print('Run: python -m pip install -r requirements-build.txt')
        return 1
    for name in ('prayerpal.py', 'BiuretPrayerPal.spec', 'icon.ico', 'assets/sounds/chime.wav',
                 'assets/sounds/adhan-omar-hisham-al-arabi.mp3', 'assets/sounds/README.md'):
        if not (ROOT / name).is_file():
            print(f'Missing required build input: {name}')
            return 1
    work, dist = ROOT / 'build', ROOT / 'dist'
    logs = ROOT / 'artifacts' / 'build'
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    build_log = logs / f'{stamp}-pyinstaller.log'
    owned = []
    success = False
    lock = build_lock(logs / '.build.lock')
    try:
        lock.__enter__()
    except OSError as error:
        print(error, file=sys.stderr)
        return 1
    try:
        for folder in (work, dist):
            prepare(folder)
            owned.append(folder)
        temporary = work / 'tmp'
        temporary.mkdir()
        environment = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(work / 'cache'),
                           TEMP=str(temporary), TMP=str(temporary), PYTHONIOENCODING='utf-8')
        command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                   '--workpath', str(work / 'pyinstaller'), '--distpath', str(dist),
                   str(ROOT / 'BiuretPrayerPal.spec')]
        description = f'Python {platform.python_version()} ({platform.machine()})'
        print(f'Building with {description}.', flush=True)
        print(f'Build log: {build_log}', flush=True)
        run(command, build_log, environment)
        candidate = dist / 'BiuretPrayerPal.exe'
        verify_executable(candidate)
        smoke_report = logs / f'{stamp}-smoke.json'
        if not arguments.skip_smoke:
            smoke_directory = work / 'smoke'
            smoke_directory.mkdir()
            smoke_environment = dict(environment, QT_QPA_PLATFORM='windows',
                                     QT_MEDIA_BACKEND='windows')
            for variable in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH',
                             'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
                smoke_environment.pop(variable, None)
            windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
            smoke_environment['PATH'] = os.pathsep.join(
                (str(windows / 'System32'), str(windows)))
            run([str(candidate), '--packaging-smoke-test', str(smoke_report)],
                logs / f'{stamp}-smoke.log', smoke_environment, timeout=60, cwd=smoke_directory)
            if not json.loads(smoke_report.read_text(encoding='utf-8')).get('passed'):
                raise RuntimeError(f'Frozen application smoke test failed: {smoke_report}')
        release = ROOT / 'release'
        release.mkdir(exist_ok=True)
        if linked(release):
            raise OSError('The release directory must not be a link or junction.')
        destination = release / candidate.name
        with tempfile.NamedTemporaryFile(dir=release, prefix='.prayerpal-',
                                         delete=False) as stream:
            publishing = Path(stream.name)
        try:
            shutil.copyfile(candidate, publishing)
            os.replace(publishing, destination)
        finally:
            publishing.unlink(missing_ok=True)
        checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
        destination.with_suffix('.exe.sha256').write_text(
            f'{checksum}  {destination.name}\n', encoding='ascii')
        shutil.copyfile(ROOT / 'packaging/THIRD_PARTY_NOTICES.txt',
                        release / 'THIRD_PARTY_NOTICES.txt')
        details = dict(timestamp_utc=stamp, python=platform.python_version(),
                       architecture=platform.machine(), dependencies=versions, sha256=checksum,
                       bytes=destination.stat().st_size, smoke_tested=not arguments.skip_smoke,
                       build_log=build_log.relative_to(ROOT).as_posix(),
                       smoke_report=smoke_report.relative_to(ROOT).as_posix(), signed=False)
        (release / 'BUILD_INFO.json').write_text(json.dumps(details, indent=2), encoding='utf-8')
        print(f'Created: {destination}\nSHA-256: {checksum}', flush=True)
        if arguments.skip_smoke:
            print('NOT SMOKE TESTED: --skip-smoke was explicitly selected.')
        success = True
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
    finally:
        if not arguments.keep_work:
            for folder in reversed(owned):
                try:
                    clean(folder)
                except OSError as error:
                    print(f'Cleanup refused/failed: {error}', file=sys.stderr)
                    success = False
        lock.__exit__(None, None, None)
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
