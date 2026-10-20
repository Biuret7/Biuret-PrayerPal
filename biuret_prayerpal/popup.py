"""Animated, screen-aware, frameless Qt toast notifications."""
from __future__ import annotations
from collections import deque
from PySide6.QtCore import (
    Qt, QObject, Signal, QTimer, QThread, QRect, QRectF, QEasingCurve, Property,
    QPropertyAnimation, QParallelAnimationGroup,
)
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import (QFrame,
                               QHBoxLayout, QLabel, QVBoxLayout, QWidget,
                               QSystemTrayIcon)
from .preferences import popup_geometry, popup_start_geometry
from .sound import SoundService
from .theme import HoverButton


class Toast(QWidget):
    closed = Signal(bool)

    def __init__(self, title: str, message: str, prefs):
        super().__init__(None)
        self.prefs = prefs
        prefs.validate()
        self.setProperty('reducedMotion', prefs.reduced_motion)
        self._zoom = 1.0
        self._snapshot = None
        self.is_closing = False
        self.user_dismissed = False
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setObjectName('toast')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 17, 17, 17)
        self.panel = QFrame()
        self.panel.setObjectName('panel')
        layout.addWidget(self.panel)
        border_color = QColor(prefs.accent)
        border_color.setAlpha(115 if prefs.border == 'glow' else 75)
        border = {
            'soft': f'1px solid {border_color.name(QColor.NameFormat.HexArgb)}',
            'glow': f'1px solid {border_color.name(QColor.NameFormat.HexArgb)}',
            'solid': f'2px solid {prefs.accent}', 'none': 'none',
        }[prefs.border]
        bg = QColor(prefs.background)
        base = f'rgba({bg.red()}, {bg.green()}, {bg.blue()}, 244)'
        deeper = f'rgba({bg.red()}, {bg.green()}, {bg.blue()}, 223)'
        self.panel.setStyleSheet(f'''
            QFrame#panel {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                            stop:0 {base}, stop:1 {deeper}); border:{border};
                            border-radius:16px; }}
            QLabel {{ background:transparent; border:none; color:{prefs.foreground};
                      font-family:'Segoe UI',Tahoma,Arial; }}
            QLabel#headline {{ font-size:15px; font-weight:800; }}
            QLabel#body {{ font-size:12px; }}
            QLabel#tag {{ color:{prefs.accent}; font-size:11px; font-weight:700; }}
            QPushButton {{ background:transparent; color:{prefs.foreground};
                           border:none; font-size:18px; padding:1px 6px; }}
            QPushButton:hover {{ color:{prefs.accent}; }}
        ''')
        inner = QVBoxLayout(self.panel)
        inner.setContentsMargins(19, 13, 19, 14)
        inner.setSpacing(7)
        top = QHBoxLayout()
        top.setSpacing(6)
        tag = QLabel('✦  BIURET PRAYERPAL')
        tag.setObjectName('tag')
        top.addWidget(tag)
        top.addStretch()
        close = HoverButton('×')
        close.setProperty('surfaceColor', prefs.background)
        close.setProperty('textColor', prefs.foreground)
        close.setProperty('accentColor', prefs.accent)
        close.setFixedSize(27, 27)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setToolTip('إغلاق الإشعار')
        close.setAccessibleName('إغلاق الإشعار وإيقاف الصوت')
        close.clicked.connect(lambda: self.close_animated(manual=True))
        top.addWidget(close)
        inner.addLayout(top)
        heading = QLabel(title)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setWordWrap(True)
        heading.setObjectName('headline')
        body = QLabel(message)
        body.setTextFormat(Qt.TextFormat.PlainText)
        body.setObjectName('body')
        body.setWordWrap(True)
        inner.addWidget(heading)
        inner.addWidget(body)
        self._group = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self.close_animated(manual=False))
        self._target = QRect()
        policy = self.panel.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.panel.setSizePolicy(policy)

    def _set_zoom(self, value):
        self._zoom = value
        self.update()

    zoom = Property(float, lambda self: self._zoom, _set_zoom)

    def paintEvent(self, event):
        painter = QPainter(self)
        # A translucent top-level surface must be cleared on every zoom frame;
        # otherwise previous scaled outlines remain in the backing store.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if self._snapshot is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.translate(self.width() / 2, self.height() / 2)
            painter.scale(self._zoom, self._zoom)
            painter.translate(-self.width() / 2, -self.height() / 2)
            painter.drawPixmap(0, 0, self._snapshot)
        elif self.prefs.border == 'glow':
            # Paint a small halo directly. A nested graphics effect on a
            # translucent window can leave capture/repaint trails during zoom.
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            for spread in range(14, 0, -1):
                color = QColor(self.prefs.accent)
                color.setAlpha(1 + (14 - spread) // 4)
                painter.setBrush(color)
                rect = QRectF(self.panel.geometry()).adjusted(-spread, -spread, spread, spread)
                painter.drawRoundedRect(rect, 16 + spread, 16 + spread)
        painter.end()

    def _placement(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            raise RuntimeError('No display is available for notifications.')
        geom = screen.availableGeometry()
        self.ensurePolished()
        width = min(390, geom.width())
        height = max(190, self.layout().heightForWidth(width))
        return QRect(*popup_geometry((geom.x(), geom.y(), geom.width(), geom.height()),
                                     (width, height), self.prefs.position))

    def _run_animation(self, start: QRect, end: QRect, opening: bool):
        if self._group is not None:
            self._group.stop()
            self._group.deleteLater()
        group = QParallelAnimationGroup(self)
        opacity = QPropertyAnimation(self, b'windowOpacity', group)
        opacity.setDuration(0 if self.prefs.reduced_motion else (260 if opening else 170))
        opacity.setStartValue(0.0 if opening else self.windowOpacity())
        opacity.setEndValue(1.0 if opening else 0.0)
        opacity.setEasingCurve(
            QEasingCurve.Type.OutCubic if opening else QEasingCurve.Type.InCubic)
        group.addAnimation(opacity)
        if start.topLeft() != end.topLeft() and not self.prefs.reduced_motion:
            geometry = QPropertyAnimation(self, b'pos', group)
            geometry.setDuration(270 if opening else 180)
            geometry.setStartValue(start.topLeft())
            geometry.setEndValue(end.topLeft())
            geometry.setEasingCurve(
                QEasingCurve.Type.OutCubic if opening else QEasingCurve.Type.InCubic)
            group.addAnimation(geometry)
        if self.prefs.animation == 'zoom' and not self.prefs.reduced_motion:
            if self._snapshot is None:
                self._snapshot = self.grab()
            self.panel.hide()
            zoom = QPropertyAnimation(self, b'zoom', group)
            zoom.setDuration(260 if opening else 170)
            zoom.setStartValue(0.92 if opening else self._zoom)
            zoom.setEndValue(1.0 if opening else 0.92)
            zoom.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(zoom)
        group.finished.connect(self._opened if opening else self._finish)
        self._group = group
        group.start()

    def display(self):
        end = self._placement()
        begin = self._start_rect(end)
        self._target = end
        self.setGeometry(begin)
        self.setWindowOpacity(0.0)
        self.show()
        self._run_animation(begin, end, True)

    def _start_rect(self, end):
        if self.prefs.animation != 'slide' or self.prefs.reduced_motion:
            return QRect(end)
        return QRect(*popup_start_geometry((end.x(), end.y(), end.width(), end.height()),
                                           self.prefs.position, 'slide'))

    def _opened(self):
        if self.is_closing:
            return
        self._snapshot = None
        self.panel.show()
        self.update()
        self._timer.start(self.prefs.duration_seconds * 1000)

    def close_animated(self, manual=False):
        if self.is_closing:
            return
        self.is_closing = True
        self.user_dismissed = manual
        self._timer.stop()
        self._run_animation(self.geometry(), self._start_rect(self._target), False)

    def discard(self):
        """Immediately remove an old preview without stacking animated windows."""
        self._timer.stop()
        self.is_closing = True
        if self._group is not None:
            self._group.stop()
        self.hide()
        self.deleteLater()

    def closeEvent(self, event):
        event.ignore()
        self.close_animated(manual=True)

    def _finish(self):
        self.hide()
        self.closed.emit(self.user_dismissed)
        self.deleteLater()


class PopupManager(QObject):
    feedback = Signal(str)

    def __init__(self, tray: QSystemTrayIcon | None = None, parent=None, sound=None):
        super().__init__(parent)
        self.tray = tray
        self.sound = sound if sound is not None else SoundService(self)
        self.sound.error_message.connect(self.feedback.emit)
        self.queue = deque()
        self.current = None
        self._request = None
        self._audio_token = None
        self._stopped = False

    def notify(self, title: str, message: str, kind: str, prefs, preview=False):
        if QThread.currentThread() != self.thread():
            raise RuntimeError('PopupManager must be used on its owning Qt thread.')
        if self._stopped:
            return
        prefs.validate()
        request = (title, message, kind, prefs, preview)
        # Tests are immediate, but never erase pending or interrupted real alerts.
        if preview:
            if self.current is not None:
                if self._request is not None and not self._request[4]:
                    self.queue.appendleft(self._request)
                self.current.discard()
                self.current = None
            self.queue.appendleft(request)
        else:
            self.queue.append(request)
        if self.tray is not None and not preview and prefs.native_fallback:
            self.tray.showMessage(title, message,
                                  QSystemTrayIcon.MessageIcon.Information, 6000)
        self._advance()

    def _advance(self):
        if self.current is not None or not self.queue:
            return
        self._request = self.queue.popleft()
        title, body, kind, prefs, _preview = self._request
        self.current = Toast(title, body, prefs)
        current = self.current
        self.current.closed.connect(lambda manual: self._finished(current, manual))
        self.current.display()
        self._audio_token = self.sound.play(prefs, kind)

    def _finished(self, toast, manually_dismissed=False):
        if self._stopped or toast is not self.current:
            return
        self.current = None
        preview = self._request[4]
        self._request = None
        # A complete Adhan recording may outlive the brief visual toast.
        # Explicitly dismissing the popup also stops audio.
        if manually_dismissed or preview:
            self.sound.stop(self._audio_token)
        self._advance()

    def shutdown(self):
        self._stopped = True
        self.queue.clear()
        self.sound.stop()
        if self.current is not None:
            self.current.discard()
            self.current = None

    def cancel_pending(self):
        """Apply changed scheduling preferences without delivering stale queued alerts."""
        self.queue.clear()
        self.sound.stop()
        if self.current is not None:
            self.current.discard()
            self.current = None
        self._request = None
