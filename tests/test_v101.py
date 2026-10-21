"""Language migration, stable reminders and transactional Windows startup tests."""
import json
import os
import subprocess
import unittest
import uuid
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from biuret_prayerpal.core import Config, calculate_day
from biuret_prayerpal.preferences import ReminderPrefs
from biuret_prayerpal.reminders import due_reminders, list_reminders
from biuret_prayerpal.startup import WindowsStartup, commit_preferences, startup_command
from biuret_prayerpal.storage import PREFERENCES_KEY, load_reminders
from test_regressions import MemorySettings


class FakeStartup:
    command = '"C:\\PrayerPal\\BiuretPrayerPal.exe" --startup'

    def __init__(self, previous=None):
        self.previous = previous
        self.calls = []

    def snapshot(self):
        return self.previous

    def set_enabled(self, enabled):
        self.calls.append(enabled)
        self.previous = (self.command, 1) if enabled else None

    def restore(self, previous):
        self.calls.append(('restore', previous))
        self.previous = previous


class V101Tests(unittest.TestCase):
    def test_old_record_preserves_sound_and_uses_opt_in_startup_arabic(self):
        settings = MemorySettings()
        old = asdict(ReminderPrefs(sound_mode='bundled_adhan', volume=17, muted=True))
        old.pop('language')
        old.pop('start_on_login')
        settings.data[PREFERENCES_KEY] = json.dumps(
            {'version': 1, 'core': asdict(Config()), 'reminders': old})
        prefs = load_reminders(settings)
        self.assertEqual((prefs.language, prefs.start_on_login), ('ar', False))
        self.assertEqual((prefs.sound_mode, prefs.volume, prefs.muted),
                         ('bundled_adhan', 17, True))
        self.assertEqual(settings.writes, [])

    def test_language_change_preserves_event_ids_times_and_sent_history(self):
        conf = Config()
        schedule = calculate_day(date(2026, 10, 20), conf)
        prefs = ReminderPrefs(early_minutes=10, morning_azkar=True, evening_azkar=True)
        arabic = list_reminders([schedule], prefs, conf.zone)
        english = list_reminders([schedule], replace(prefs, language='en'), conf.zone)
        self.assertEqual([(event.identity, event.when) for event in arabic],
                         [(event.identity, event.when) for event in english])
        self.assertTrue(all(not any('\u0600' <= char <= '\u06ff'
                                    for char in event.title + event.body) for event in english))
        self.assertEqual(due_reminders(english[0].when, english, {arabic[0].identity}), [])

    def test_startup_command_quotes_paths_and_uses_no_shell(self):
        exe = Path('C:/Program Files/PrayerPal/BiuretPrayerPal.exe').resolve()
        self.assertEqual(startup_command(exe, frozen=True), f'"{exe}" --startup')
        script = Path('C:/Arabic folder/PrayerPal/prayerpal.py').resolve()
        with patch.object(Path, 'is_file', return_value=True):
            command = startup_command('C:/Python/python.exe', frozen=False, script=script)
        expected = subprocess.list2cmdline(
            [str(Path('C:/Python/pythonw.exe').resolve()), str(script), '--startup'])
        self.assertEqual(command, expected)

    def test_startup_changes_commit_together_and_rollback_on_save_failure(self):
        for previous, enabled in ((None, True), (('old command', 1), False),
                                  (('old command', 1), True)):
            with self.subTest(previous=previous, enabled=enabled):
                settings, startup = MemorySettings(), FakeStartup(previous)
                prefs = ReminderPrefs(language='en', start_on_login=enabled)
                settings.fail = True
                with self.assertRaises(OSError):
                    commit_preferences(settings, Config(), prefs, startup)
                self.assertEqual(startup.previous, previous)
                self.assertEqual(startup.calls[-1], ('restore', previous))
                self.assertNotIn(PREFERENCES_KEY, settings.data)
                settings.fail = False
                commit_preferences(settings, Config(), prefs, startup)
                self.assertEqual(load_reminders(settings), prefs)
                self.assertEqual(startup.previous, (startup.command, 1) if enabled else None)

    def test_invalid_preferences_and_registration_failure_do_not_write_settings(self):
        for invalid in (ReminderPrefs(language='fr'), ReminderPrefs(start_on_login=1)):
            startup, settings = FakeStartup(), MemorySettings()
            with self.assertRaises(ValueError):
                commit_preferences(settings, Config(), invalid, startup)
            self.assertEqual(startup.calls, [])
            self.assertEqual(settings.writes, [])
        startup, settings = FakeStartup(), MemorySettings()
        with patch.object(startup, 'set_enabled', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                commit_preferences(settings, Config(), ReminderPrefs(start_on_login=True), startup)
        self.assertEqual(settings.writes, [])

    @unittest.skipUnless(os.name == 'nt', 'Real HKCU registry integration')
    def test_real_registry_round_trip_only_in_unique_test_namespace(self):
        import winreg
        key = 'Software\\BiuretPrayerPalTest-' + uuid.uuid4().hex
        startup = WindowsStartup(key=key, command='"C:\\Test App\\PrayerPal.exe" --startup')
        try:
            self.assertFalse(startup.enabled())
            startup.set_enabled(True)
            self.assertEqual(startup.snapshot(), (startup.command, winreg.REG_SZ))
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
                winreg.SetValueEx(handle, 'Unrelated', 0, winreg.REG_SZ, 'keep')
            startup.set_enabled(False)
            self.assertIsNone(startup.snapshot())
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
                self.assertEqual(winreg.QueryValueEx(handle, 'Unrelated')[0], 'keep')
            startup.restore(('previous command', winreg.REG_SZ))
            self.assertEqual(startup.snapshot()[0], 'previous command')
        finally:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
            except FileNotFoundError:
                pass
