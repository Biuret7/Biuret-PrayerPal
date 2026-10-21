"""Offline astronomical prayer-time estimates (not an official awqaf timetable)."""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

APP_NAME = "Biuret PrayerPal"
APP_VERSION = "1.0.1"
DEFAULT_TZ = "Asia/Hebron"
PRAYERS = (
    ("Fajr", "الفجر"),
    ("Dhuhr", "الظهر"),
    ("Asr", "العصر"),
    ("Maghrib", "المغرب"),
    ("Isha", "العشاء"),
)
PRAYER_KEYS = tuple(name for name, _ in PRAYERS)
AR_NAMES = dict(PRAYERS)
# Approximate city centers; they are not mosque coordinates.
CITIES = {
    "رام الله": (31.9038, 35.2034),
    "القدس": (31.7683, 35.2137),
    "نابلس": (32.2211, 35.2544),
    "الخليل": (31.5326, 35.0998),
    "غزة": (31.5017, 34.4668),
    "جنين": (32.4607, 35.3009),
    "بيت لحم": (31.7054, 35.2024),
}
UTC = timezone.utc
LOG = logging.getLogger("PrayerPal")


@dataclass
class Config:
    city: str = "رام الله"
    lat: float = 31.9038
    lon: float = 35.2034
    tz_name: str = DEFAULT_TZ
    fajr_angle: float = 18.0
    isha_angle: float = 17.0
    asr_shadow: int = 1              # 1: majority; 2: Hanafi
    offsets: dict[str, int] = field(default_factory=lambda: {key: 0 for key in PRAYER_KEYS})
    alerts: bool = True
    early_minutes: int = 0
    dark: bool = True
    time_24: bool = True

    def validate(self) -> None:
        for name in ('alerts', 'dark', 'time_24'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'Invalid boolean setting: {name}')
        if not isinstance(self.city, str) or not self.city.strip():
            raise ValueError("أدخل اسم المدينة.")
        for name in ('lat', 'lon', 'fajr_angle', 'isha_angle'):
            if type(getattr(self, name)) not in (int, float):
                raise ValueError(f'Invalid numeric setting: {name}')
        if not isinstance(self.offsets, dict):
            raise ValueError('تصحيحات الدقائق غير صالحة.')
        if not math.isfinite(self.lat) or not -90 <= self.lat <= 90:
            raise ValueError("خط العرض يجب أن يكون بين -90 و90.")
        if not math.isfinite(self.lon) or not -180 <= self.lon <= 180:
            raise ValueError("خط الطول يجب أن يكون بين -180 و180.")
        for angle in (self.fajr_angle, self.isha_angle):
            if not math.isfinite(angle) or not 10 <= angle <= 22:
                raise ValueError("زاوية الفجر والعشاء يجب أن تكون بين 10 و22 درجة.")
        if type(self.asr_shadow) is not int or self.asr_shadow not in (1, 2):
            raise ValueError("طريقة العصر غير صحيحة.")
        if type(self.early_minutes) is not int or self.early_minutes not in (0, 5, 10, 15, 30):
            raise ValueError("مدة التنبيه المبكر غير مدعومة.")
        for name in PRAYER_KEYS:
            minutes = self.offsets.get(name, 0)
            if type(minutes) is not int or not -30 <= minutes <= 30:
                raise ValueError("تصحيح الدقائق يجب أن يكون بين -30 و30.")
        try:
            ZoneInfo(self.tz_name)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise ValueError(
                "تعذّر تحميل المنطقة الزمنية. على Windows شغّل: py -m pip install tzdata"
            ) from exc

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz_name)


@dataclass(frozen=True)
class Schedule:
    day: date
    times: dict[str, datetime]
    sunrise: datetime


def _solar_coordinates(instant: datetime) -> tuple[float, float]:
    """Return (solar declination in degrees, equation of time in minutes).

    NOAA solar-calculation equations based on Jean Meeus, Astronomical Algorithms.
    The instant is treated as UTC, regardless of its input timezone.
    """
    jd = instant.astimezone(UTC).timestamp() / 86400.0 + 2440587.5
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360.0
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    ecc = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    mr = math.radians(m)
    l0r = math.radians(l0)
    center = (math.sin(mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
              + math.sin(2 * mr) * (0.019993 - 0.000101 * t)
              + math.sin(3 * mr) * 0.000289)
    omega = math.radians(125.04 - 1934.136 * t)
    sun_long = math.radians(l0 + center - 0.00569 - 0.00478 * math.sin(omega))
    mean_obliquity = 23.0 + \
        (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    obliquity = math.radians(mean_obliquity + 0.00256 * math.cos(omega))
    dec = math.degrees(math.asin(math.sin(obliquity) * math.sin(sun_long)))
    y = math.tan(obliquity / 2.0) ** 2
    eq = 4.0 * math.degrees(
        y * math.sin(2 * l0r) - 2 * ecc * math.sin(mr)
        + 4 * ecc * y * math.sin(mr) * math.cos(2 * l0r)
        - 0.5 * y * y * math.sin(4 * l0r)
        - 1.25 * ecc * ecc * math.sin(2 * mr)
    )
    return dec, eq


def _utc_midnight(value: datetime) -> datetime:
    utc_value = value.astimezone(UTC)
    return utc_value.replace(hour=0, minute=0, second=0, microsecond=0)


def _nearest_utc_day(candidate: datetime, anchor: datetime) -> datetime:
    """Select the solar-day UTC occurrence closest to the local noon."""
    day_shift = round((anchor - candidate).total_seconds() / 86400)
    return candidate + timedelta(days=day_shift)


def _solar_noon(day: date, conf: Config) -> datetime:
    """Solve solar transit iteratively, allowing for UTC date rollover."""
    local_noon = datetime.combine(day, time(12, 0), tzinfo=conf.zone).astimezone(UTC)
    midnight = _utc_midnight(local_noon)
    estimate = local_noon
    for _ in range(5):
        _, eq = _solar_coordinates(estimate)
        candidate = midnight + timedelta(minutes=720 - 4 * conf.lon - eq)
        estimate = _nearest_utc_day(candidate, local_noon)
    return estimate


def _event_time(noon: datetime, conf: Config, morning: bool,
                angle_at_decl) -> datetime:
    """Solve a solar-altitude crossing using updated declination and equation of time."""
    midnight = _utc_midnight(noon)
    estimate = noon + timedelta(hours=-6 if morning else 6)
    lat_rad = math.radians(conf.lat)
    for _ in range(6):
        dec, eq = _solar_coordinates(estimate)
        dec_rad = math.radians(dec)
        altitude = math.radians(angle_at_decl(dec))
        denominator = math.cos(lat_rad) * math.cos(dec_rad)
        if abs(denominator) < 1e-9:
            raise ValueError("لا يمكن حساب المواقيت لهذه الإحداثيات في هذا التاريخ.")
        cos_hour = (math.sin(altitude) - math.sin(lat_rad) * math.sin(dec_rad)) / denominator
        if not -1 <= cos_hour <= 1:
            raise ValueError("لا يوجد شروق/غروب أو شفق فلكي لهذا اليوم في الموقع المختار.")
        degrees = math.degrees(math.acos(cos_hour))
        offset = -4 * degrees if morning else 4 * degrees
        candidate = midnight + timedelta(minutes=720 - 4 * conf.lon - eq + offset)
        estimate = _nearest_utc_day(candidate, noon)
    return estimate


def _round_minute(utc_time: datetime, zone: ZoneInfo) -> datetime:
    rounded = (utc_time + timedelta(seconds=30)).replace(second=0, microsecond=0)
    return rounded.astimezone(zone)


def calculate_day(day: date, conf: Config) -> Schedule:
    """Offline calculations. 18° Fajr / 17° Isha are defaults, not an official timetable."""
    conf.validate()
    noon = _solar_noon(day, conf)
    def horizon(_dec): return -0.833  # solar refraction and solar radius at the horizon
    sunrise = _event_time(noon, conf, True, horizon)
    maghrib = _event_time(noon, conf, False, horizon)
    # At higher latitudes the requested twilight angle may not be reached.
    # Use the common angle/60 fraction-of-night fallback only in that case.
    try:
        fajr = _event_time(noon, conf, True, lambda _dec: -conf.fajr_angle)
    except ValueError:
        previous_noon = _solar_noon(day - timedelta(days=1), conf)
        previous_sunset = _event_time(previous_noon, conf, False, horizon)
        fajr = sunrise - (sunrise - previous_sunset) * (conf.fajr_angle / 60.0)
    try:
        isha = _event_time(noon, conf, False, lambda _dec: -conf.isha_angle)
    except ValueError:
        next_noon = _solar_noon(day + timedelta(days=1), conf)
        next_sunrise = _event_time(next_noon, conf, True, horizon)
        isha = maghrib + (next_sunrise - maghrib) * (conf.isha_angle / 60.0)

    def asr_altitude(dec: float) -> float:
        return math.degrees(math.atan(1.0 / (
            conf.asr_shadow + math.tan(math.radians(abs(conf.lat - dec)))
        )))

    asr = _event_time(noon, conf, False, asr_altitude)
    events = dict(zip(PRAYER_KEYS, (fajr, noon, asr, maghrib, isha)))
    zone = conf.zone
    prayers = {
        key: _round_minute(value + timedelta(minutes=conf.offsets.get(key, 0)), zone)
        for key, value in events.items()
    }
    sunrise_local = _round_minute(sunrise, zone)
    instants = [prayers[k].astimezone(UTC) for k in PRAYER_KEYS]
    if not all(a < b for a, b in zip(instants, instants[1:])):
        raise ValueError("ترتيب المواقيت غير متوقع، راجع إعدادات الموقع والتصحيحات.")
    if not all(value.astimezone(zone).date() == day for value in instants):
        raise ValueError("المنطقة الزمنية لا تطابق موقع الشمس؛ راجع الموقع والمنطقة الزمنية.")
    return Schedule(day=day, times=prayers, sunrise=sunrise_local)


def next_and_previous(now: datetime, schedules: list[Schedule]):
    if now.tzinfo is None:
        raise ValueError("Now must be timezone-aware")
    if any(value.tzinfo is None for schedule in schedules for value in schedule.times.values()):
        raise ValueError('Schedule times must be timezone-aware')
    events = sorted(
        ((key, instant) for schedule in schedules for key, instant in schedule.times.items()),
        key=lambda item: item[1].astimezone(UTC),
    )
    current = now.astimezone(UTC)
    past = [event for event in events if event[1].astimezone(UTC) <= current]
    future = [event for event in events if event[1].astimezone(UTC) > current]
    return (past[-1] if past else None, future[0] if future else None)


def time_text(value: datetime, twenty_four: bool) -> str:
    if twenty_four:
        return value.strftime("%H:%M")
    return value.strftime("%I:%M") + (" ص" if value.hour < 12 else " م")


def countdown_text(now: datetime, target: datetime) -> str:
    if now.tzinfo is None or target.tzinfo is None:
        raise ValueError('Countdown times must be timezone-aware')
    diff = max(0, math.ceil((target.astimezone(UTC) - now.astimezone(UTC)).total_seconds()))
    hours, remain = divmod(diff, 3600)
    minute, seconds = divmod(remain, 60)
    return f"{hours:02d}:{minute:02d}:{seconds:02d}"
