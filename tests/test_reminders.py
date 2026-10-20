import unittest
from datetime import date, timedelta
from biuret_prayerpal.core import Config, calculate_day
from biuret_prayerpal.preferences import (
    ReminderPrefs, popup_geometry, popup_start_geometry, POSITIONS,
)
from biuret_prayerpal.reminders import due_reminders, list_reminders, prune_sent


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.conf = Config()
        self.schedule = calculate_day(date(2026, 10, 18), self.conf)

    def test_reminders_and_azkar(self):
        prefs = ReminderPrefs(early_minutes=10, morning_azkar=True, evening_azkar=True)
        events = list_reminders([self.schedule], prefs, self.conf.zone)
        self.assertEqual(len(events), 12)
        self.assertEqual(len(set(event.identity for event in events)), 12)
        self.assertTrue(any(event.kind == 'azkar' for event in events))

    def test_alerts_disabled(self):
        self.assertEqual(list_reminders(
            [self.schedule], ReminderPrefs(enabled=False), self.conf.zone), [])

    def test_due_and_dedup(self):
        events = list_reminders([self.schedule], ReminderPrefs(), self.conf.zone)
        prayer = next(e for e in events if e.identity.endswith(':Fajr:prayer'))
        self.assertEqual(
            due_reminders(
                prayer.when +
                timedelta(
                    seconds=33),
                events,
                set()),
            [prayer])
        self.assertEqual(due_reminders(prayer.when +
                                       timedelta(seconds=33), events, {prayer.identity}), [])
        self.assertEqual(due_reminders(prayer.when + timedelta(seconds=91), events, set()), [])
        self.assertEqual(due_reminders(prayer.when - timedelta(seconds=1), events, set()), [])

    def test_prune_ids(self):
        result = prune_sent(
            {'2026-10-18:Fajr:prayer', '2026-10-10:Isha:prayer'}, date(2026, 10, 18))
        self.assertEqual(result, {'2026-10-18:Fajr:prayer'})

    def test_geometry_all_positions(self):
        screen = (-1200, -100, 1200, 900)
        for name in POSITIONS:
            with self.subTest(name=name):
                x, y, w, h = popup_geometry(screen, (344, 147), name)
                self.assertLessEqual(-1200, x)
                self.assertLessEqual(-100, y)
                self.assertLessEqual(x + w, 0)
                self.assertLessEqual(y + h, 800)
                for animation in ('fade', 'slide', 'zoom'):
                    geom = popup_start_geometry((x, y, w, h), name, animation)
                    self.assertEqual(len(geom), 4)
                    self.assertTrue(all(isinstance(v, int) for v in geom))

    def test_validation(self):
        for kw in ({'volume': 101}, {'position': 'bad'}, {'background': 'red'},
                   {'morning_time': '25:11'}, {'duration_seconds': 2}):
            with self.subTest(kwargs=kw), self.assertRaises(ValueError):
                ReminderPrefs().with_updates(**kw)
