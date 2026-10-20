"""Validated, Qt-independent reminder and pop-up configuration."""
from __future__ import annotations
from dataclasses import dataclass, replace
import re

POSITIONS = {
    'top_right': 'أعلى اليمين',
    'top_left': 'أعلى اليسار',
    'bottom_right': 'أسفل اليمين',
    'bottom_left': 'أسفل اليسار',
    'center': 'وسط الشاشة',
}
ANIMATIONS = {'fade': 'تلاشي', 'slide': 'انزلاق', 'zoom': 'تكبير'}
SOUND_MODES = {
    'chime': 'نغمة هادئة',
    'bundled_adhan': 'أذان عمر هشام العربي (مرفق)',
    'adhan': 'ملف أذان',
    'azkar': 'ملف صوت أذكار',
    'none': 'بدون صوت'}
BORDERS = {'soft': 'هادئ', 'glow': 'متوهج', 'solid': 'واضح', 'none': 'بلا إطار'}
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


@dataclass(frozen=True)
class ReminderPrefs:
    enabled: bool = True
    early_minutes: int = 0
    morning_azkar: bool = False
    evening_azkar: bool = False
    morning_time: str = '08:00'
    evening_time: str = '18:00'
    position: str = 'bottom_right'
    animation: str = 'slide'
    duration_seconds: int = 8
    sound_mode: str = 'chime'
    adhan_file: str = ''
    azkar_file: str = ''
    volume: int = 55
    muted: bool = False
    background: str = '#12252D'
    foreground: str = '#EFFBF7'
    accent: str = '#6BE3BE'
    border: str = 'glow'
    native_fallback: bool = False
    reduced_motion: bool = False

    def validate(self) -> None:
        for name in ('enabled', 'morning_azkar', 'evening_azkar', 'muted',
                     'native_fallback', 'reduced_motion'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'Invalid boolean preference: {name}')
        for name in ('early_minutes', 'volume', 'duration_seconds'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'Invalid integer preference: {name}')
        for name in ('adhan_file', 'azkar_file'):
            if not isinstance(getattr(self, name), str):
                raise ValueError('مسار الصوت يجب أن يكون نصاً.')
        for key, options in (
            (self.position, POSITIONS), (self.animation, ANIMATIONS),
            (self.sound_mode, SOUND_MODES), (self.border, BORDERS),
        ):
            if not isinstance(key, str) or key not in options:
                raise ValueError('إعداد الإشعارات يحتوي خياراً غير مدعوم.')
        if self.early_minutes not in (0, 5, 10, 15, 30):
            raise ValueError('مدة التذكير المبكر غير صحيحة.')
        if not 0 <= self.volume <= 100:
            raise ValueError('مستوى الصوت يجب أن يكون بين 0 و100.')
        if not 4 <= self.duration_seconds <= 30:
            raise ValueError('مدة ظهور الإشعار يجب أن تكون بين 4 و30 ثانية.')
        for color in (self.background, self.foreground, self.accent):
            if not isinstance(color, str) or not HEX.fullmatch(color):
                raise ValueError('اللون يجب أن يكون بصيغة #RRGGBB.')
        for value in (self.morning_time, self.evening_time):
            if not isinstance(value, str) or not re.fullmatch(r'[0-9]{2}:[0-9]{2}', value):
                raise ValueError('وقت الأذكار يجب أن يكون بصيغة HH:MM.')
            try:
                h, m = map(int, value.split(':'))
            except (TypeError, ValueError) as exc:
                raise ValueError('وقت الأذكار يجب أن يكون بصيغة HH:MM.') from exc
            if len(value) != 5 or not 0 <= h <= 23 or not 0 <= m <= 59:
                raise ValueError('وقت الأذكار خارج النطاق الصحيح.')

    def with_updates(self, **changes) -> 'ReminderPrefs':
        updated = replace(self, **changes)
        updated.validate()
        return updated


def popup_geometry(screen: tuple[int, int, int, int], popup_size: tuple[int, int],
                   position: str, margin: int = 20) -> tuple[int, int, int, int]:
    """Position inside *available* display geometry, including negative monitor origins."""
    if position not in POSITIONS:
        raise ValueError('موضع غير صالح')
    sx, sy, sw, sh = screen
    if sw <= 0 or sh <= 0 or min(popup_size) <= 0 or margin < 0:
        raise ValueError('Display and popup dimensions must be positive.')
    margin = min(margin, (sw - 1) // 2, (sh - 1) // 2)
    width = min(popup_size[0], sw - margin * 2)
    height = min(popup_size[1], sh - margin * 2)
    if position == 'center':
        x, y = sx + (sw - width) // 2, sy + (sh - height) // 2
    else:
        x = sx + margin if position.endswith('left') else sx + sw - width - margin
        y = sy + margin if position.startswith('top') else sy + sh - height - margin
    return (x, y, width, height)


def popup_start_geometry(end: tuple[int, int, int, int], position: str,
                         animation: str) -> tuple[int, int, int, int]:
    """Slide the fixed layout; fade/painted zoom keep its final geometry."""
    if position not in POSITIONS or animation not in ANIMATIONS:
        raise ValueError('Invalid popup transition')
    x, y, w, h = end
    if animation == 'slide':
        if position.endswith('left'):
            return (x - 45, y, w, h)
        if position.endswith('right'):
            return (x + 45, y, w, h)
        return (x, y + 40, w, h)
    return end
