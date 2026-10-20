"""Regression coverage for clock boundaries, persistence failure and audio I/O."""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from biuret_prayerpal.core import Config, Schedule, UTC, calculate_day, countdown_text
from biuret_prayerpal.preferences import POSITIONS, ReminderPrefs, popup_geometry
from biuret_prayerpal.reminders import due_reminders, list_reminders, prune_sent
from biuret_prayerpal.sound import write_chime
from biuret_prayerpal.storage import (
    PREFERENCES_KEY, load_core, load_reminders, load_sent, parse_bool,
    save_preferences, save_sent,
)


class MemorySettings:
    def __init__(self):
        self.data = {}
        self.fail = False
        self.writes = []

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value
        self.writes.append(key)

    def remove(self, key):
        self.data.pop(key, None)

    def sync(self):
        pass

    def status(self):
        return SimpleNamespace(name='AccessError' if self.fail else 'NoError')


class ClockRegressionTests(unittest.TestCase):
    def test_early_alert_uses_elapsed_minutes_through_both_dst_changes(self):
        zone = ZoneInfo('America/New_York')
        for prayer in (datetime(2026, 3, 8, 3, 5, tzinfo=zone),
                       datetime(2026, 11, 1, 1, 5, fold=1, tzinfo=zone)):
            with self.subTest(prayer=prayer):
                schedule = Schedule(prayer.date(), {'Fajr': prayer}, prayer)
                events = list_reminders([schedule], ReminderPrefs(early_minutes=15), zone)
                early = next(event for event in events if event.kind == 'early')
                self.assertEqual(prayer.astimezone(UTC) - early.when.astimezone(UTC),
                                 timedelta(minutes=15))
                self.assertEqual(due_reminders(early.when, events, set()), [early])

    def test_azkar_gap_shifts_forward_and_fold_fires_once(self):
        zone = ZoneInfo('America/New_York')
        gap = list_reminders([], ReminderPrefs(morning_azkar=True, morning_time='02:30'),
                             zone, days=[date(2026, 3, 8)])[0]
        self.assertEqual((gap.when.hour, gap.when.minute), (3, 30))
        folded = list_reminders([], ReminderPrefs(morning_azkar=True, morning_time='01:30'),
                                zone, days=[date(2026, 11, 1)])[0]
        self.assertEqual(folded.when.fold, 0)
        self.assertEqual(due_reminders(folded.when.replace(fold=1), [folded], set()), [])

    def test_duplicates_and_delivery_window_boundaries(self):
        conf = Config()
        schedule = calculate_day(date(2026, 10, 20), conf)
        events = list_reminders([schedule, schedule], ReminderPrefs(), conf.zone)
        self.assertEqual(len(events), 5)
        event = events[0]
        self.assertEqual(due_reminders(event.when, [event, event], set()), [event])
        self.assertEqual(
            due_reminders(
                event.when +
                timedelta(
                    seconds=89.999),
                events,
                set()),
            [event])
        self.assertEqual(due_reminders(event.when + timedelta(seconds=90), events, set()), [])
        with self.assertRaises(ValueError):
            due_reminders(event.when.replace(tzinfo=None), events, set())
        with self.assertRaises(ValueError):
            due_reminders(
                event.when, [
                    replace(
                        event, when=event.when.replace(
                            tzinfo=None))], set())

    def test_azkar_independent_of_astronomical_failure(self):
        conf = Config(lat=89, lon=0, tz_name='UTC')
        with self.assertRaises(ValueError):
            calculate_day(date(2026, 12, 21), conf)
        events = list_reminders([], ReminderPrefs(morning_azkar=True, evening_azkar=True),
                                conf.zone, days=[date(2026, 12, 21)])
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event.kind == 'azkar' for event in events))

    def test_countdown_uses_utc_and_rejects_naive_times(self):
        zone = ZoneInfo('America/New_York')
        first = datetime(2026, 11, 1, 1, 0, tzinfo=zone)
        second = first.replace(fold=1)
        self.assertEqual(countdown_text(first, second), '01:00:00')
        with self.assertRaises(ValueError):
            countdown_text(first.replace(tzinfo=None), second)

    def test_utc_date_rollover_cities(self):
        for conf in (Config(city='Sydney', lat=-33.87, lon=151.21, tz_name='Australia/Sydney'),
                     Config(city='San Francisco', lat=37.77, lon=-122.42,
                            tz_name='America/Los_Angeles')):
            schedule = calculate_day(date(2026, 10, 20), conf)
            self.assertEqual({value.date() for value in schedule.times.values()}, {schedule.day})


class PreferenceRegressionTests(unittest.TestCase):
    def test_malformed_preferences_raise_value_errors(self):
        for changes in ({'volume': float('nan')}, {'volume': True}, {'muted': 'false'},
                        {'position': []}, {'accent': None}, {'morning_time': None},
                        {'morning_time': ' 1:30'}, {'adhan_file': 42}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                ReminderPrefs().with_updates(**changes)
        for conf in (Config(lat='bad'), Config(dark='false'), Config(offsets=[]),
                     Config(offsets={'Fajr': True})):
            with self.assertRaises(ValueError):
                conf.validate()

    def test_tiny_and_negative_origin_monitors_keep_every_position_inside(self):
        for screen in ((-100, -40, 12, 9), (-1920, 0, 1920, 1080), (0, 0, 1, 1)):
            sx, sy, sw, sh = screen
            for position in POSITIONS:
                x, y, width, height = popup_geometry(screen, (390, 190), position)
                self.assertTrue(sx <= x <= x + width <= sx + sw)
                self.assertTrue(sy <= y <= y + height <= sy + sh)

    def test_corrupt_field_keeps_mute_city_and_other_preferences(self):
        settings = MemorySettings()
        conf = Config(city='Custom city')
        prefs = ReminderPrefs(muted=True, position='center', volume=37)
        save_preferences(settings, conf, prefs)
        payload = json.loads(settings.data[PREFERENCES_KEY])
        payload['reminders']['volume'] = 999
        settings.data[PREFERENCES_KEY] = json.dumps(payload)
        recovered = load_reminders(settings)
        self.assertTrue(recovered.muted)
        self.assertEqual(recovered.position, 'center')
        self.assertEqual(recovered.volume, ReminderPrefs().volume)
        self.assertEqual(load_core(settings).city, 'Custom city')

    def test_one_record_commit_and_rollback_preserve_previous_pair(self):
        settings = MemorySettings()
        settings.data['city'] = 'Legacy city'
        original = Config(), ReminderPrefs(muted=True)
        save_preferences(settings, *original)
        self.assertEqual(settings.writes, [PREFERENCES_KEY])
        before = settings.data[PREFERENCES_KEY]
        settings.fail = True
        with self.assertRaises(OSError):
            save_preferences(settings, Config(city='New city'), ReminderPrefs(volume=12))
        self.assertEqual(settings.data[PREFERENCES_KEY], before)
        self.assertEqual(load_reminders(settings), original[1])
        self.assertEqual(settings.data['city'], 'Legacy city')

    def test_failed_first_write_removes_uncommitted_record(self):
        settings = MemorySettings()
        settings.fail = True
        with self.assertRaises(OSError):
            save_preferences(settings, Config(), ReminderPrefs())
        self.assertNotIn(PREFERENCES_KEY, settings.data)

    def test_persisted_ledger_prevents_restart_duplicate(self):
        settings = MemorySettings()
        conf = Config()
        events = list_reminders([calculate_day(date(2026, 10, 20), conf)],
                                ReminderPrefs(), conf.zone)
        event = events[0]
        save_sent(settings, {event.identity, 'broken',
                  '2099-01-01:Fajr:prayer'}, date(2026, 10, 20))
        ledger = load_sent(settings, date(2026, 10, 20))
        self.assertEqual(ledger, {event.identity})
        self.assertEqual(due_reminders(event.when, events, ledger), [])
        self.assertEqual(prune_sent({'2026-01-01:a', 'bad'}, date(2026, 10, 20)), set())

    def test_unknown_boolean_uses_explicit_default(self):
        self.assertTrue(parse_bool('garbage', True))
        self.assertFalse(parse_bool('garbage', False))
        self.assertFalse(parse_bool('off', True))


class AtomicAudioTests(unittest.TestCase):
    def test_large_but_corrupt_chime_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'chime.wav'
            path.write_bytes(b'corrupt' * 3000)
            write_chime(path)
            self.assertEqual(path.read_bytes()[:4], b'RIFF')
            before = path.stat().st_mtime_ns
            write_chime(path)
            self.assertEqual(path.stat().st_mtime_ns, before)

    def test_publish_failure_keeps_old_bytes_and_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'chime.wav'
            path.write_bytes(b'old bytes')
            with patch('biuret_prayerpal.sound.os.replace', side_effect=PermissionError):
                with self.assertRaises(PermissionError):
                    write_chime(path)
            self.assertEqual(path.read_bytes(), b'old bytes')
            self.assertEqual(list(Path(directory).iterdir()), [path])
