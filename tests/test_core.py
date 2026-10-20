import unittest
from datetime import date, timedelta
from biuret_prayerpal.core import (Config, CITIES, calculate_day,
                                   next_and_previous, countdown_text)


class PrayerMathTests(unittest.TestCase):
    def test_all_palestinian_cities_seasonally(self):
        for city, (lat, lon) in CITIES.items():
            conf = Config(city=city, lat=lat, lon=lon)
            for day in (date(2026, 1, 15), date(2026, 4, 15),
                        date(2026, 7, 15), date(2026, 10, 15)):
                with self.subTest(city=city, day=day):
                    schedule = calculate_day(day, conf)
                    series = [schedule.times[key]
                              for key in ('Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha')]
                    self.assertTrue(all(series[i] < series[i + 1] for i in range(4)))
                    self.assertEqual({time.date() for time in series}, {day})
                    self.assertTrue(series[0] < schedule.sunrise < series[1])

    def test_daylight_savings(self):
        conf = Config()
        before = calculate_day(date(2026, 3, 27), conf)
        after = calculate_day(date(2026, 4, 1), conf)
        self.assertNotEqual(before.times['Dhuhr'].utcoffset(), after.times['Dhuhr'].utcoffset())

    def test_after_isha_next_fajr(self):
        conf = Config()
        today = calculate_day(date(2026, 10, 18), conf)
        tomorrow = calculate_day(date(2026, 10, 19), conf)
        now = today.times['Isha'] + timedelta(minutes=3)
        _past, upcoming = next_and_previous(now, [today, tomorrow])
        self.assertEqual(upcoming, ('Fajr', tomorrow.times['Fajr']))
        self.assertNotEqual(countdown_text(now, upcoming[1]), '00:00:00')

    def test_asr_and_offset(self):
        day = date(2026, 10, 18)
        basic = calculate_day(day, Config())
        later = calculate_day(day, Config(asr_shadow=2))
        self.assertGreater(later.times['Asr'], basic.times['Asr'])
        offsets = {key: 5 if key == 'Fajr' else 0
                   for key in ('Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha')}
        shifted = calculate_day(day, Config(offsets=offsets))
        self.assertEqual((shifted.times['Fajr'] - basic.times['Fajr']).total_seconds(), 300)

    def test_invalid_coordinate(self):
        for conf in (Config(lat=100), Config(lon=float('nan')),
                     Config(isha_angle=2), Config(asr_shadow=9)):
            with self.assertRaises(ValueError):
                conf.validate()
