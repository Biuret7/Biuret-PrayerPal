"""Obsidian glass palette and paint-only Qt micro-interactions.

No CSS transition declarations or widget geometry changes are used for buttons.
"""
from __future__ import annotations

import math

from PySide6.QtCore import (
    QEvent, Property, QPropertyAnimation, QEasingCurve, Qt, QRectF, QPointF,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractSpinBox, QCheckBox, QComboBox, QLineEdit, QPushButton, QSlider, QWidget,
)

PALETTES = {
    True: dict(bg='#0B1018', card='#141E2A', card_alt='#1C2B39', fg='#EDF5F8',
               muted='#A2B5C5', stroke='#304455', emerald='#70E1BA', cyan='#78D9EE',
               gold='#E9C881', row='#193B39', button='#1A2938', hero1='#173B3C',
               hero2='#132732', primary_text='#092C25'),
    False: dict(bg='#EFF5F7', card='#FFFFFF', card_alt='#E7F0F3', fg='#16313F',
                muted='#506876', stroke='#BACDD6', emerald='#08745D', cyan='#096C85',
                gold='#94600F', row='#D7EEE7', button='#E1EBF0', hero1='#155C54',
                hero2='#123F4A', primary_text='#FFFFFF'),
}


def style(dark: bool) -> str:
    c = PALETTES[dark]
    return f'''
    QWidget {{ color:{c['fg']}; font-family:'Segoe UI','Tahoma'; font-size:13px; }}
    QMainWindow, QDialog, QWidget#central {{ background:{c['bg']}; }}
    QLabel {{ background:transparent; }}
    QLabel#brand {{ font-size:21px; font-weight:700; }}
    QLabel#caption, QLabel#hint, QLabel#status, QLabel#subtitle {{
        color:{c['muted']}; font-size:12px; }}
    QLabel#heading {{ font-size:15px; font-weight:700; }}
    QLabel#accent {{ color:{c['gold']}; font-size:12px; font-weight:600; }}
    QFrame#hero {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c['hero1']},stop:1 {c['hero2']});
        border:1px solid {c['emerald']}; border-radius:20px; }}
    QFrame#hero QLabel {{ color:#EFFAF6; background:transparent; border:none; }}
    QLabel#nextPrayer {{ font-size:29px; font-weight:700; }}
    QLabel#countdown {{ font-family:'Cascadia Code',Consolas; font-size:34px;
        font-weight:600; color:#A9FFE5; }}
    QFrame#times {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c['card_alt']},stop:1 {c['card']});
        border:1px solid {c['stroke']}; border-radius:16px; }}
    QFrame#prayerRow {{ background:transparent; border:none; border-radius:9px; }}
    QFrame#prayerRow[active="true"] {{ background:{c['row']}; border:1px solid {c['emerald']}; }}
    QFrame#prayerRow QLabel {{ border:none; background:transparent; }}
    QLabel#prayerName {{ font-size:14px; font-weight:600; }}
    QLabel#prayerTime {{ color:{c['emerald']}; font-family:'Cascadia Code',Consolas;
        font-size:16px; font-weight:600; }}
    QPushButton {{ border:1px solid {c['stroke']}; border-radius:10px; background:{c['button']};
        min-height:24px; padding:7px 12px; font-weight:600; }}
    QPushButton:hover, QPushButton:focus {{ border-color:{c['cyan']}; }}
    QPushButton:pressed {{ background:{c['row']}; }}
    QPushButton:disabled {{ color:{c['muted']}; background:{c['card']}; }}
    QPushButton#primary {{ background:{c['emerald']}; color:{c['primary_text']}; }}
    QPushButton#tiny {{ min-width:32px; max-width:32px; min-height:30px; padding:4px; }}
    QTabWidget::pane {{ border:1px solid {c['stroke']}; background:{c['card']};
        border-radius:14px; }}
    QTabBar::tab {{ padding:10px 14px; background:{c['button']}; border:1px solid transparent;
        border-radius:8px; margin:3px 2px; }}
    QTabBar::tab:hover {{ color:{c['cyan']}; }}
    QTabBar::tab:selected {{ background:{c['row']}; color:{c['emerald']};
        border-color:{c['stroke']}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit {{
        background:{c['card_alt']}; border:1px solid {c['stroke']}; border-radius:8px;
        padding:7px 9px; min-height:24px; selection-background-color:{c['emerald']};
        selection-color:{c['primary_text']}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
    QDoubleSpinBox:focus, QTimeEdit:focus {{
        border-color:{c['cyan']}; }}
    QComboBox QAbstractItemView {{ background:{c['card']}; color:{c['fg']};
        selection-background-color:{c['row']}; selection-color:{c['fg']}; padding:6px; }}
    QComboBox::drop-down {{ border:none; background:transparent; width:25px; }}
    QComboBox::down-arrow {{ image:none; }}
    QCheckBox {{ spacing:10px; padding:6px 2px; }}
    QCheckBox::indicator {{ width:18px; height:18px; border-radius:6px;
        border:1px solid {c['stroke']}; background:{c['button']}; }}
    QCheckBox::indicator:checked {{ background:{c['emerald']}; border:3px solid {c['hero2']}; }}
    QCheckBox::indicator:hover {{ border-color:{c['cyan']}; }}
    QCheckBox:disabled {{ color:{c['muted']}; }}
    QSlider::groove:horizontal {{ background:{c['stroke']}; height:5px; border-radius:2px; }}
    QSlider::sub-page:horizontal {{ background:{c['emerald']}; border-radius:2px; }}
    QSlider::handle:horizontal {{ background:{c['cyan']}; border:2px solid {c['card']};
        border-radius:9px; width:14px; margin:-6px 0; }}
    QSlider::handle:horizontal:hover {{ background:{c['gold']}; }}
    QScrollArea {{ border:none; background:transparent; }}
    QScrollArea > QWidget > QWidget {{ background:{c['card']}; }}
    QScrollBar:vertical {{ width:8px; background:{c['card']}; margin:3px; }}
    QScrollBar::handle:vertical {{ background:{c['stroke']}; border-radius:3px; min-height:28px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QMenu {{ background:{c['card']}; border:1px solid {c['stroke']}; padding:6px; }}
    QMenu::item {{ padding:8px 24px; border-radius:6px; }}
    QMenu::item:selected {{ background:{c['row']}; color:{c['emerald']}; }}
    QToolTip {{ background:{c['card_alt']}; color:{c['fg']};
        border:1px solid {c['cyan']}; padding:6px; }}
    '''


def _palette(widget):
    dark = widget.window().property('darkTheme')
    colors = PALETTES[dark if isinstance(dark, bool) else True].copy()
    for property_name, keys in (
        ('surfaceColor', ('button', 'card_alt')), ('textColor', ('fg',)),
        ('accentColor', ('cyan', 'stroke')),
    ):
        custom = widget.property(property_name)
        if custom:
            for key in keys:
                colors[key] = custom
    return colors


def _mix(first, second, amount):
    a, b = QColor(first), QColor(second)
    return QColor.fromRgbF(*(a.getRgbF()[i] * (1 - amount) + b.getRgbF()[i] * amount
                             for i in range(4)))


class HoverButton(QPushButton):
    """Animated color and press scale painted within a stable layout rectangle."""

    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._progress = 0.0
        self._scale = 1.0
        self._hover = QPropertyAnimation(self, b'hoverProgress', self)
        self._press = QPropertyAnimation(self, b'pressScale', self)
        for animation in (self._hover, self._press):
            animation.setDuration(160)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.pressed.connect(lambda: self._animate(self._press, self._scale, 0.97))
        self.released.connect(lambda: self._animate(self._press, self._scale, 1.0))

    def _set_progress(self, value):
        self._progress = value
        self.update()

    def _set_scale(self, value):
        self._scale = value
        self.update()

    hoverProgress = Property(float, lambda self: self._progress, _set_progress)
    pressScale = Property(float, lambda self: self._scale, _set_scale)

    def _animate(self, animation, start, end):
        animation.stop()
        if self.window().property('reducedMotion'):
            self.setProperty(animation.propertyName().data().decode(), end)
            return
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.start()

    def enterEvent(self, event):
        self._animate(self._hover, self._progress, 1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate(self._hover, self._progress, 1.0 if self.hasFocus() else 0.0)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self._animate(self._hover, self._progress, 1.0)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._animate(self._hover, self._progress, 1.0 if self.underMouse() else 0.0)
        super().focusOutEvent(event)

    def paintEvent(self, event):
        c = _palette(self)
        primary = self.objectName() == 'primary'
        progress = self._progress if self.isEnabled() else 0.0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        painter.setBrush(_mix(c['emerald'] if primary else c['button'],
                              c['cyan'] if primary else c['card_alt'], progress))
        painter.setPen(QPen(_mix(c['emerald'] if primary else c['stroke'], c['cyan'], progress),
                            2 if self.hasFocus() else 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        painter.setPen(QColor(c['primary_text'] if primary else c['fg'])
                       if self.isEnabled() else QColor(c['muted']))
        painter.setFont(self.font())
        symbol = self.property('symbol')
        if symbol:
            self._paint_symbol(painter, symbol)
        else:
            flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextShowMnemonic
            painter.drawText(self.rect(), flags, self.text())
        painter.end()

    def _paint_symbol(self, painter, symbol):
        center = QPointF(self.width() / 2, self.height() / 2)
        painter.setPen(QPen(painter.pen().color(), 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        ring = QRectF(center.x() - 6, center.y() - 6, 12, 12)
        if symbol == 'sun':
            painter.drawEllipse(ring.adjusted(2, 2, -2, -2))
            for index in range(8):
                angle = math.pi * index / 4
                direction = QPointF(math.cos(angle), math.sin(angle))
                painter.drawLine(center + direction * 6, center + direction * 8)
        elif symbol == 'moon':
            painter.drawArc(ring, 70 * 16, 270 * 16)
            painter.drawArc(ring.translated(3, -2), 170 * 16, 150 * 16)
        else:
            painter.drawArc(ring, 40 * 16, 290 * 16)
            painter.drawLine(center + QPointF(5, -5), center + QPointF(5, 0))
            painter.drawLine(center + QPointF(5, 0), center + QPointF(0, -1))


class _InteractionRing(QWidget):
    """Transparent, paint-only child; never changes input geometry or event delivery."""

    def __init__(self, control):
        super().__init__(control)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._strength = 0.0
        self.animation = QPropertyAnimation(self, b'strength', self)
        self.animation.setDuration(160)
        control.installEventFilter(self)
        self.setGeometry(control.rect())
        self.show()

    def _set_strength(self, value):
        self._strength = value
        self.update()

    strength = Property(float, lambda self: self._strength, _set_strength)

    def eventFilter(self, control, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(control.rect())
        if event.type() in (QEvent.Type.Enter, QEvent.Type.Leave, QEvent.Type.FocusIn,
                            QEvent.Type.FocusOut, QEvent.Type.EnabledChange):
            target = (1.0 if control.hasFocus() else 0.45 if control.underMouse() else 0.0)
            if not control.isEnabled():
                target = 0.0
            self.animation.stop()
            if control.window().property('reducedMotion'):
                self._set_strength(target)
            else:
                self.animation.setStartValue(self._strength)
                self.animation.setEndValue(target)
                self.animation.start()
            self.raise_()
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(_palette(self)['cyan'])
        color.setAlphaF(self._strength * 0.8)
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        control = self.parentWidget()
        if isinstance(control, QComboBox):
            rtl = control.layoutDirection() == Qt.LayoutDirection.RightToLeft
            x = 13 if rtl else self.width() - 13
            y = self.height() / 2
            painter.setPen(QPen(QColor(_palette(self)['fg']), 1.5))
            painter.drawLine(QPointF(x - 3, y - 2), QPointF(x, y + 1))
            painter.drawLine(QPointF(x, y + 1), QPointF(x + 3, y - 2))
        painter.end()


def install_interactions(root):
    for widget in root.findChildren(QWidget):
        if isinstance(widget, (QLineEdit, QComboBox, QAbstractSpinBox, QCheckBox, QSlider)):
            # Spin boxes own line edits; one outer ring is sufficient.
            if isinstance(widget.parentWidget(), (QComboBox, QAbstractSpinBox)):
                continue
            if not hasattr(widget, '_interaction_ring'):
                widget._interaction_ring = _InteractionRing(widget)
