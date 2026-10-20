"""Pure reminder scheduling; event IDs prevent duplicated prayer and Azkar alerts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from .core import AR_NAMES, Schedule, UTC
from .preferences import ReminderPrefs


@dataclass(frozen=True)
class ReminderEvent:
    identity: str
    title: str
    body: str
    kind: str
    when: datetime


def _azkar_instant(day: date, hhmm: str, zone) -> datetime:
    """Choose the first fold; shift nonexistent DST times forward by the gap."""
    hour, minute = (int(v) for v in hhmm.split(':'))
    local = datetime.combine(day, time(hour, minute), tzinfo=zone)
    return local.astimezone(UTC).astimezone(zone)


def list_reminders(schedules: list[Schedule], prefs: ReminderPrefs, zone,
                   *, days: list[date] | None = None) -> list[ReminderEvent]:
    """Build prayer alerts and independent daily Azkar alerts.

    Explicit days allow Azkar to continue when astronomical calculations fail
    (for example, during polar night). Prayer identities remain date based even
    when an early reminder occurs on the preceding day.
    """
    prefs.validate()
    if not prefs.enabled:
        return []
    result: list[ReminderEvent] = []
    for schedule in schedules:
        day = schedule.day.isoformat()
        for prayer, instant in schedule.times.items():
            if instant.tzinfo is None:
                raise ValueError('Prayer times must contain timezone')
            result.append(ReminderEvent(
                f'{day}:{prayer}:prayer', 'حان وقت الصلاة',
                f'حان الآن وقت صلاة {AR_NAMES[prayer]}. تقبّل الله طاعتكم.',
                'prayer', instant))
            if prefs.early_minutes:
                result.append(ReminderEvent(
                    f'{day}:{prayer}:early', 'اقترب وقت الصلاة',
                    f'تبقى {prefs.early_minutes} دقائق على صلاة {AR_NAMES[prayer]}.',
                    'early', (instant.astimezone(UTC) - timedelta(
                        minutes=prefs.early_minutes)).astimezone(zone)))
    azkar_days = {schedule.day for schedule in schedules} | set(days or [])
    for azkar_day in sorted(azkar_days):
        day = azkar_day.isoformat()
        if prefs.morning_azkar:
            result.append(ReminderEvent(
                f'{day}:azkar:morning', 'أذكار الصباح',
                'لحظات من الذكر والاستغفار لبداية يومك.', 'azkar',
                _azkar_instant(azkar_day, prefs.morning_time, zone)))
        if prefs.evening_azkar:
            result.append(ReminderEvent(
                f'{day}:azkar:evening', 'أذكار المساء',
                'خصص دقائق لأذكار المساء والطمأنينة.', 'azkar',
                _azkar_instant(azkar_day, prefs.evening_time, zone)))
    unique = {event.identity: event for event in result}
    return sorted(unique.values(), key=lambda r: r.when.astimezone(UTC))


def due_reminders(now: datetime, events: list[ReminderEvent], sent: set[str],
                  window_seconds: int = 90) -> list[ReminderEvent]:
    if now.tzinfo is None:
        raise ValueError('now must contain timezone')
    if window_seconds <= 0:
        raise ValueError('The delivery window must be positive.')
    if any(event.when.tzinfo is None for event in events):
        raise ValueError('Reminder times must contain timezone')
    current = now.astimezone(UTC)
    due = {}
    for event in events:
        if (event.identity not in sent and
                0 <= (current - event.when.astimezone(UTC)).total_seconds() < window_seconds):
            due.setdefault(event.identity, event)
    return sorted(due.values(), key=lambda event: event.when.astimezone(UTC))


def prune_sent(sent: set[str], today: date, keep_days: int = 2) -> set[str]:
    threshold = today - timedelta(days=keep_days)
    result = set()
    for item in sent:
        try:
            day = date.fromisoformat(item[:10])
        except (TypeError, ValueError):
            continue
        if threshold <= day <= today + timedelta(days=1):
            result.add(item)
    return result
