import tempfile
import unittest
import wave
from pathlib import Path
from biuret_prayerpal.core import Config
from biuret_prayerpal.preferences import ReminderPrefs
from biuret_prayerpal.storage import load_core, save_core, load_reminders, save_reminders
from biuret_prayerpal.sound import write_chime


class DummyStatus:
    name = 'NoError'


class SettingsStub:
    def __init__(self): self.data = {}
    def value(self, k, default=None): return self.data.get(k, default)
    def setValue(self, k, value): self.data[k] = value
    def sync(self): pass
    def status(self): return DummyStatus()


class StorageAudioTests(unittest.TestCase):
    def test_save_load(self):
        q = SettingsStub()
        c = Config(city='رام الله', lat=31.9038)
        p = ReminderPrefs(position='center', animation='zoom', muted=True,
                          volume=0, accent='#FFCC00', morning_azkar=True)
        save_core(q, c)
        save_reminders(q, p)
        self.assertEqual(load_core(q), c)
        self.assertEqual(load_reminders(q), p)

    def test_migration(self):
        q = SettingsStub()
        q.setValue('notifications', False)
        q.setValue('early_alert', 15)
        p = load_reminders(q)
        self.assertFalse(p.enabled)
        self.assertEqual(p.early_minutes, 15)

    def test_invalid_pref_fallback(self):
        q = SettingsStub()
        q.setValue('reminder/volume', 400)
        self.assertEqual(load_reminders(q), ReminderPrefs())

    def test_chime(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'beep.wav'
            self.assertEqual(write_chime(path), path)
            self.assertEqual(write_chime(path), path)
            with wave.open(str(path), 'rb') as wave_file:
                self.assertEqual(wave_file.getnchannels(), 1)
                self.assertEqual(wave_file.getframerate(), 22050)
                self.assertGreater(wave_file.getnframes(), 10000)
