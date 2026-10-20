"""Validated settings, legacy migration, and one-record preference commits.

The canonical JSON record keeps core and reminder settings together. Legacy
QSettings keys remain untouched, allowing recovery and migration from v3/v4.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, fields, replace
from datetime import date

from .core import Config, PRAYER_KEYS
from .preferences import ReminderPrefs
from .reminders import prune_sent

LOG = logging.getLogger(__name__)
PREFERENCES_KEY = 'preferences/v1'
CORE_KEYS = {
    'city': 'city', 'lat': 'lat', 'lon': 'lon', 'tz_name': 'tz',
    'fajr_angle': 'fajr_angle', 'isha_angle': 'isha_angle',
    'asr_shadow': 'asr_shadow', 'alerts': 'notifications',
    'early_minutes': 'early_alert', 'dark': 'dark_theme', 'time_24': '24hour',
}


def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {'true', '1', 'yes', 'on'}:
        return True
    if text in {'false', '0', 'no', 'off'}:
        return False
    return default


def cast(value, default):
    if value is None:
        return default
    try:
        if isinstance(default, bool):
            return parse_bool(value, default)
        if isinstance(default, str) and not isinstance(value, str):
            return default
        if type(default) is int and isinstance(value, float) and not value.is_integer():
            return default
        return type(default)(value)
    except (ValueError, TypeError, OverflowError):
        return default


def _record(settings):
    raw = settings.value(PREFERENCES_KEY, '')
    if not raw:
        return {}
    try:
        record = json.loads(raw)
        if not isinstance(record, dict) or record.get('version') != 1:
            raise ValueError('Unsupported settings record')
        if not all(isinstance(record.get(key), dict) for key in ('core', 'reminders')):
            raise ValueError('Invalid settings sections')
        return record
    except (TypeError, ValueError):
        LOG.warning('Invalid preference record; reading preserved legacy settings.')
        return {}


def _validated_fields(model, raw):
    """Recover individual damaged fields without unmuting/resetting everything."""
    current = model()
    for field in fields(model):
        if field.name not in raw:
            continue
        default = getattr(current, field.name)
        value = cast(raw[field.name], default)
        if field.name == 'offsets':
            if not isinstance(raw[field.name], dict):
                continue
            value = {}
            for key in PRAYER_KEYS:
                minutes = cast(raw[field.name].get(key), 0)
                value[key] = minutes if -30 <= minutes <= 30 else 0
        candidate = replace(current, **{field.name: value})
        try:
            candidate.validate()
        except (ValueError, TypeError):
            LOG.warning('Invalid preference field reset: %s', field.name)
        else:
            current = candidate
    return current


def load_core(settings) -> Config:
    record = _record(settings)
    if record:
        return _validated_fields(Config, record['core'])
    raw = {name: settings.value(key) for name, key in CORE_KEYS.items()}
    raw['offsets'] = {key: settings.value(f'offset/{key}', 0) for key in PRAYER_KEYS}
    return _validated_fields(Config, raw)


def load_reminders(settings) -> ReminderPrefs:
    record = _record(settings)
    if record:
        return _validated_fields(ReminderPrefs, record['reminders'])
    defaults = ReminderPrefs()
    raw = {}
    for field in fields(ReminderPrefs):
        default = getattr(defaults, field.name)
        previous = {'enabled': 'notifications', 'early_minutes': 'early_alert'}.get(field.name)
        fallback = settings.value(previous, default) if previous else default
        raw[field.name] = settings.value(f'reminder/{field.name}', fallback)
    return _validated_fields(ReminderPrefs, raw)


def _write_checked(settings, key, value):
    old_value = settings.value(key)
    try:
        settings.setValue(key, value)
        settings.sync()
        if settings.status().name != 'NoError':
            raise OSError('تعذّر حفظ الإعدادات. لم يتم تطبيق التغييرات.')
    except (OSError, RuntimeError) as error:
        # Best-effort rollback of the in-memory QSettings cache too; otherwise
        # its destructor could later flush a change reported as unsuccessful.
        try:
            if old_value is None:
                settings.remove(key)
            else:
                settings.setValue(key, old_value)
            settings.sync()
        except (OSError, RuntimeError):
            LOG.error('Settings rollback could not be flushed.')
        raise OSError('تعذّر حفظ الإعدادات. تحقق من صلاحية الكتابة.') from error


def save_preferences(settings, conf: Config, prefs: ReminderPrefs) -> None:
    conf.validate()
    prefs.validate()
    # ReminderPrefs owns these values; keep the legacy Config mirrors coherent.
    conf = replace(conf, alerts=prefs.enabled, early_minutes=prefs.early_minutes)
    payload = json.dumps({'version': 1, 'core': asdict(conf), 'reminders': asdict(prefs)},
                         ensure_ascii=False, allow_nan=False)
    _write_checked(settings, PREFERENCES_KEY, payload)


def save_core(settings, conf: Config) -> None:
    prefs = replace(
        load_reminders(settings),
        enabled=conf.alerts,
        early_minutes=conf.early_minutes)
    save_preferences(settings, conf, prefs)


def save_reminders(settings, prefs: ReminderPrefs) -> None:
    save_preferences(settings, load_core(settings), prefs)


def load_sent(settings, today: date) -> set[str]:
    try:
        items = json.loads(settings.value('runtime/sent', '[]'))
        if not isinstance(items, list):
            return set()
        return prune_sent({item for item in items if isinstance(item, str)}, today)
    except (TypeError, ValueError):
        return set()


def save_sent(settings, sent: set[str], today: date) -> None:
    _write_checked(settings, 'runtime/sent', json.dumps(sorted(prune_sent(sent, today))))
