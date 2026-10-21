"""Opt-in, current-user Windows startup registration; no administrator access."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def startup_command(executable=None, *, frozen=None, script=None):
    executable = Path(executable or sys.executable).resolve()
    frozen = bool(getattr(sys, 'frozen', False)) if frozen is None else frozen
    if frozen:
        return f'"{executable}" --startup'
    pythonw = executable.with_name('pythonw.exe')
    interpreter = pythonw if pythonw.is_file() else executable
    script = Path(script or Path(__file__).resolve().parents[1] / 'prayerpal.py').resolve()
    return subprocess.list2cmdline([str(interpreter), str(script), '--startup'])


class WindowsStartup:
    VALUE = 'BiuretPrayerPal'
    KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'

    def __init__(self, *, key=None, command=None):
        self.key = key or self.KEY
        self.command = command or startup_command()

    def snapshot(self):
        if os.name != 'nt':
            return None
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.key) as handle:
                return winreg.QueryValueEx(handle, self.VALUE)
        except FileNotFoundError:
            return None

    def enabled(self):
        return self.snapshot() is not None

    def restore(self, previous):
        if os.name != 'nt':
            if previous is not None:
                raise OSError('Startup registration is available on Windows only.')
            return
        import winreg
        if previous is None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.key, 0,
                                    winreg.KEY_SET_VALUE) as handle:
                    winreg.DeleteValue(handle, self.VALUE)
            except FileNotFoundError:
                pass
        else:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, self.key, 0,
                                    winreg.KEY_SET_VALUE) as handle:
                winreg.SetValueEx(handle, self.VALUE, 0, previous[1], previous[0])

    def set_enabled(self, enabled):
        if os.name != 'nt' and enabled:
            raise OSError('Startup registration is available on Windows only.')
        self.restore((self.command, 1) if enabled else None)


def commit_preferences(settings, conf, prefs, startup):
    """Restore the previous Run value if the preference write fails."""
    from .storage import save_preferences
    conf.validate()
    prefs.validate()
    previous = startup.snapshot()
    changed = bool(previous) != prefs.start_on_login
    if changed or (prefs.start_on_login and previous[0] != startup.command):
        startup.set_enabled(prefs.start_on_login)
        changed = True
    try:
        save_preferences(settings, conf, prefs)
    except OSError as error:
        if changed:
            try:
                startup.restore(previous)
            except OSError as rollback_error:
                message = ('Settings could not be saved and Windows startup could not be '
                           'restored. Review the startup option before retrying.')
                raise OSError(message) from rollback_error
        raise error
