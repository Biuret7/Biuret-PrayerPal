"""Compact main window and background scheduler for Biuret PrayerPal."""
from __future__ import annotations
import logging
from dataclasses import replace
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QSettings, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox,
    QSystemTrayIcon, QVBoxLayout, QWidget, QStackedWidget, QGraphicsOpacityEffect,
)
from .core import PRAYERS, calculate_day, countdown_text, next_and_previous
from .preferences import ReminderPrefs
from .reminders import due_reminders, list_reminders, prune_sent
from .storage import load_core, load_reminders, save_preferences, load_sent, save_sent
from .popup import PopupManager
from .theme import style, HoverButton, ThemeButton
from .i18n import tr, error_text, translate_tree, display_time, prayer_name
from .startup import WindowsStartup, commit_preferences
from .dialogs import SettingsDialog
from .resources import resource_path

LOG = logging.getLogger('biuret_prayerpal')


def app_icon() -> QIcon:
    icon_file = resource_path('icon.ico')
    if icon_file.is_file():
        return QIcon(str(icon_file))
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#103C35'))
    painter.drawRoundedRect(0, 0, 64, 64, 16, 16)
    painter.setBrush(QColor('#72F3C7'))
    painter.drawEllipse(14, 12, 37, 37)
    painter.setBrush(QColor('#103C35'))
    painter.drawEllipse(26, 4, 37, 37)
    painter.setBrush(QColor('#F8D88A'))
    painter.drawEllipse(45, 43, 5, 5)
    painter.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self, settings=None, *, enable_tray=True, startup=None):
        super().__init__()
        # Reuse v3 registry keys to retain prior saved location and offsets.
        self.settings = settings if settings is not None else QSettings('MyApps', 'PrayerReminder')
        self.conf = load_core(self.settings)
        self.prefs = load_reminders(self.settings)
        self.startup = startup if startup is not None else WindowsStartup()
        self._theme_overlay = None
        self.day_loaded = None
        self.schedules = {}
        self.events = []
        self.sent = load_sent(self.settings, datetime.now(self.conf.zone).date())
        self._settings_dialog = None
        self.last_error = ''
        self.setWindowTitle('Biuret PrayerPal | مواقيت الصلاة')
        self.setWindowIcon(app_icon())
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.prefs.language == 'ar'
                                else Qt.LayoutDirection.LeftToRight)
        self.resize(480, 670)
        self.setMinimumSize(440, 610)
        self._build_ui()
        self._build_tray(enable_tray)
        self.popups = PopupManager(self.tray if self.tray_available else None, self)
        self.popups.feedback.connect(self._notice)
        self.popups.sound.active_changed.connect(self._audio_state_changed)
        self._apply_theme()
        self._refresh()
        self.clock = QTimer(self)
        self.clock.timeout.connect(self._tick)
        self.clock.start(1000)
        QApplication.instance().aboutToQuit.connect(self.clock.stop)
        QApplication.instance().aboutToQuit.connect(self.popups.shutdown)

    @staticmethod
    def _label(text, name):
        widget = QLabel(text)
        widget.setObjectName(name)
        return widget

    def _build_ui(self):
        outer_widget = QWidget()
        outer_widget.setObjectName('central')
        self.setCentralWidget(outer_widget)
        layout = QVBoxLayout(outer_widget)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(16)
        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(37, 37))
        header.addWidget(icon)
        name_block = QVBoxLayout()
        name_block.setSpacing(0)
        name_block.addWidget(self._label('Biuret PrayerPal', 'brand'))
        self.city_label = self._label('رفيقك لمواقيت الصلاة', 'caption')
        name_block.addWidget(self.city_label)
        header.addLayout(name_block)
        header.addStretch()
        refresh = HoverButton('↻')
        refresh.setObjectName('tiny')
        refresh.setProperty('symbol', 'refresh')
        refresh.setToolTip('تحديث المواقيت')
        refresh.setAccessibleName('تحديث المواقيت')
        refresh.clicked.connect(lambda: self._refresh(True))
        header.addWidget(refresh)
        self.theme = ThemeButton()
        self.theme.setObjectName('tiny')
        self.theme.setToolTip('الوضع الداكن/الفاتح')
        self.theme.setAccessibleName('تبديل المظهر الداكن والفاتح')
        self.theme.clicked.connect(self._toggle_theme)
        header.addWidget(self.theme)
        self.language_button = HoverButton('EN' if self.prefs.language == 'ar' else 'AR')
        self.language_button.setFixedWidth(44)
        self.language_button.setToolTip('English' if self.prefs.language == 'ar' else 'العربية')
        self.language_button.clicked.connect(self._toggle_language)
        header.addWidget(self.language_button)
        layout.addLayout(header)

        hero = QFrame()
        hero.setObjectName('hero')
        hero.setMinimumHeight(164)
        inner = QVBoxLayout(hero)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(1)
        title = self._label('الصلاة القادمة', 'subtitle')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_name = self._label('جاري الحساب...', 'nextPrayer')
        self.next_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_name.setMinimumHeight(32)
        self.countdown = self._label('--:--:--', 'countdown')
        self.countdown.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown.setMinimumHeight(34)
        self.next_hint = self._label('', 'subtitle')
        self.next_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(title)
        inner.addWidget(self.next_name)
        inner.addWidget(self.countdown)
        inner.addWidget(self.next_hint)
        layout.addWidget(hero)

        row = QHBoxLayout()
        row.addWidget(self._label('مواقيت اليوم', 'heading'))
        row.addStretch()
        self.current_prayer = self._label('', 'caption')
        row.addWidget(self.current_prayer)
        layout.addLayout(row)
        box = QFrame()
        box.setObjectName('times')
        times_layout = QVBoxLayout(box)
        times_layout.setContentsMargins(8, 6, 8, 6)
        times_layout.setSpacing(1)
        self.audio_stack = QStackedWidget()
        self.audio_stack.setFixedWidth(145)
        self.audio_stack.setFixedHeight(42)
        self.audio_idle = self._label('الصوت متوقف', 'caption')
        self.audio_idle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_idle.setToolTip('يظهر زر إيقاف الصوت أثناء تشغيل تسجيل فقط.')
        self.audio_stack.addWidget(self.audio_idle)
        self.stop_audio_button = HoverButton('إيقاف الصوت')
        self.stop_audio_button.setEnabled(False)
        self.stop_audio_button.setToolTip('إيقاف التسجيل حتى بعد اختفاء الإشعار')
        self.stop_audio_button.clicked.connect(self._stop_audio)
        self.audio_stack.addWidget(self.stop_audio_button)
        self.sunrise = self._label('الشروق --:--', 'caption')
        self.sunrise.setToolTip('الشروق معلومة فلكية لليوم، وليس الصلاة الحالية أو القادمة.')
        self.rows = {}
        for name, arabic in PRAYERS:
            item = QFrame()
            item.setObjectName('prayerRow')
            item.setProperty('active', 'false')
            item.setMinimumHeight(43)
            item_line = QHBoxLayout(item)
            item_line.setContentsMargins(13, 0, 13, 0)
            item_line.addWidget(self._label(arabic, 'prayerName'))
            item_line.addStretch()
            value = self._label('--:--', 'prayerTime')
            value.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item_line.addWidget(value)
            times_layout.addWidget(item)
            self.rows[name] = (item, value)
        layout.addWidget(box)
        details = QHBoxLayout()
        details.addWidget(self.sunrise)
        details.addStretch()
        details.addWidget(self.audio_stack)
        layout.addLayout(details)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)
        settings_button = HoverButton('الإعدادات')
        settings_button.clicked.connect(self._open_settings)
        test_button = HoverButton('اختبار تنبيه')
        test_button.clicked.connect(self._test_notification)
        hide_button = HoverButton('إخفاء للخلفية')
        hide_button.setObjectName('primary')
        hide_button.clicked.connect(self._hide_to_tray)
        for button in (settings_button, test_button, hide_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.status = self._label('حساب محلي • لا يحتاج إنترنت', 'status')
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(34)
        layout.addWidget(self.status)
        layout.addStretch(0)
        translate_tree(self.centralWidget(), self.prefs.language)
        self.setWindowTitle(tr('Biuret PrayerPal | مواقيت الصلاة', self.prefs.language))

    def _build_tray(self, enabled=True):
        self.tray_available = enabled and QSystemTrayIcon.isSystemTrayAvailable()
        self.tray = QSystemTrayIcon(app_icon(), self)
        menu = QMenu(self)
        menu.setLayoutDirection(self.layoutDirection())
        actions = (
            ('فتح البرنامج', self._show_window),
            ('الإعدادات', self._open_settings),
            ('اختبار التذكير', self._test_notification),
            ('تحديث المواقيت', lambda: self._refresh(True)),
            ('إيقاف الصوت', self._stop_audio),
            ('خروج نهائي', self._quit),
        )
        for i, (title, handler) in enumerate(actions):
            if i == len(actions) - 1:
                menu.addSeparator()
            action = QAction(tr(title, self.prefs.language), self)
            action.triggered.connect(handler)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._activated)
        if self.tray_available:
            self.tray.show()

    def _apply_theme(self, animate=False):
        self.setProperty('darkTheme', self.conf.dark)
        self.setProperty('reducedMotion', self.prefs.reduced_motion)
        self.setStyleSheet(style(self.conf.dark))
        self.theme.set_dark(self.conf.dark, animate=animate)
        for widget, _ in self.rows.values():
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _notice(self, message: str, error: bool = True):
        message = error_text(message, self.prefs.language) if error else tr(
            message, self.prefs.language)
        self.status.setText(message)
        self.status.setToolTip(message)
        self.status.setStyleSheet('color:#FF9D9D;' if error else '')
        if error:
            LOG.warning(message)

    def _toggle_theme(self):
        new_conf = replace(self.conf, dark=not self.conf.dark)
        try:
            save_preferences(self.settings, new_conf, self.prefs)
        except OSError as error:
            self._notice(str(error))
            return
        self.conf = new_conf
        snapshot = self.centralWidget().grab() if not self.prefs.reduced_motion else None
        if self._theme_overlay is not None:
            self._theme_overlay.hide()
            self._theme_overlay.deleteLater()
            self._theme_overlay = None
        self._apply_theme(animate=True)
        if snapshot is not None and self.isVisible():
            overlay = QLabel(self.centralWidget())
            overlay.setPixmap(snapshot)
            overlay.setGeometry(self.centralWidget().rect())
            overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            effect = QGraphicsOpacityEffect(overlay)
            overlay.setGraphicsEffect(effect)
            fade = QPropertyAnimation(effect, b'opacity', overlay)
            fade.setDuration(220)
            fade.setStartValue(1.0)
            fade.setEndValue(0.0)
            fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade.finished.connect(overlay.deleteLater)
            overlay.destroyed.connect(lambda: self._clear_theme_overlay(overlay))
            overlay.show()
            overlay.raise_()
            self._theme_overlay = overlay
            fade.start()

    def _clear_theme_overlay(self, overlay):
        if self._theme_overlay is overlay:
            self._theme_overlay = None

    def resizeEvent(self, event):
        if self._theme_overlay is not None:
            self._theme_overlay.hide()
            self._theme_overlay.deleteLater()
            self._theme_overlay = None
        super().resizeEvent(event)

    def _toggle_language(self):
        new_prefs = replace(self.prefs, language='en' if self.prefs.language == 'ar' else 'ar')
        try:
            save_preferences(self.settings, self.conf, new_prefs)
        except OSError as error:
            self._notice(str(error))
            return
        self.prefs = new_prefs
        self._rebuild_presentation()
        self._refresh()

    def _rebuild_presentation(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.prefs.language == 'ar'
                                else Qt.LayoutDirection.LeftToRight)
        if self._theme_overlay is not None:
            self._theme_overlay.hide()
            self._theme_overlay.deleteLater()
            self._theme_overlay = None
        self._build_ui()
        menu = self.tray.contextMenu()
        for action, title in zip((a for a in menu.actions() if not a.isSeparator()),
                                 ('فتح البرنامج', 'الإعدادات', 'اختبار التذكير',
                                  'تحديث المواقيت', 'إيقاف الصوت', 'خروج نهائي')):
            action.setText(tr(title, self.prefs.language))
        menu.setLayoutDirection(self.layoutDirection())
        self._apply_theme()
        self._audio_state_changed(self.popups.sound.is_active)

    def _audio_state_changed(self, active):
        self.stop_audio_button.setEnabled(active)
        self.audio_stack.setCurrentIndex(1 if active else 0)

    def _refresh(self, manual=False):
        try:
            now = datetime.now(self.conf.zone)
            # Do not recalculate a known-invalid polar day every second.
            self.day_loaded = now.date()
            self.schedules = {shift: calculate_day(
                now.date() + timedelta(days=shift), self.conf) for shift in (-1, 0, 1)}
            self.day_loaded = now.date()
            self.events = list_reminders(list(self.schedules.values()), self.prefs, self.conf.zone)
            self.last_error = ''
        except (ValueError, OverflowError) as error:
            self.last_error = str(error)
            LOG.exception('Prayer calculation error')
            self.events = list_reminders([], self.prefs, self.conf.zone, days=[now.date()])
            self.schedules = {}
            self.next_name.setText(tr('تعذّر الحساب', self.prefs.language))
            self.countdown.setText('--:--:--')
            self.next_hint.setText(tr('راجع الإعدادات', self.prefs.language))
            self.sunrise.setText('—')
            self.current_prayer.setText('—')
            for widget, value in self.rows.values():
                value.setText('--:--')
                self._highlight(widget, False)
            self._notice('خطأ في حساب المواقيت — اضغط تحديث للتفاصيل')
            if manual:
                QMessageBox.warning(self, tr('تعذّر حساب المواقيت', self.prefs.language),
                                    error_text(self.last_error, self.prefs.language))
            return
        self._notice('تم تحديث المواقيت' if manual else 'حساب محلي • لا يحتاج إنترنت', False)
        self._tick()

    def _highlight(self, frame, active):
        value = 'true' if active else 'false'
        if frame.property('active') != value:
            frame.setProperty('active', value)
            frame.style().unpolish(frame)
            frame.style().polish(frame)
            frame.update()

    def _tick(self):
        now = datetime.now(self.conf.zone)
        if self.day_loaded != now.date():
            self._refresh()
            return
        language = self.prefs.language
        self.city_label.setText(f'{tr(self.conf.city, language)}  •  {now:%d/%m/%Y}')
        self._deliver_reminders(now)
        if not self.schedules:
            return
        today = self.schedules[0]
        self.sunrise.setText(tr('الشروق اليوم: {time}', language,
                                time=display_time(today.sunrise, self.conf.time_24, language)))
        previous, upcoming = next_and_previous(now, [self.schedules[i] for i in (-1, 0, 1)])
        current = tr('الصلاة الحالية: {prayer}', language,
                     prayer=prayer_name(previous[0], language)) if previous else ''
        self.current_prayer.setText(current)
        for name, (frame, value) in self.rows.items():
            value.setText(display_time(today.times[name], self.conf.time_24, language))
            self._highlight(frame, bool(upcoming and upcoming[0] == name
                                        and upcoming[1] == today.times[name]))
        if upcoming:
            prayer, instant = upcoming
            self.next_name.setText(prayer_name(prayer, language))
            self.countdown.setText(countdown_text(now, instant))
            day_text = 'غداً' if instant.astimezone(
                self.conf.zone).date() != today.day else 'اليوم'
            self.next_hint.setText(f'{tr(day_text, language)}  •  '
                                   f'{display_time(instant, self.conf.time_24, language)}')
            if self.tray_available:
                self.tray.setToolTip(f'Biuret PrayerPal • {prayer_name(prayer, language)} '
                                     f'{tr(day_text, language)}')
        else:
            self.next_name.setText(tr('لا توجد صلاة قادمة', language))
            self.countdown.setText('--:--:--')

    def _deliver_reminders(self, now):
        due = due_reminders(now, self.events, self.sent)
        for event in due:
            self.sent.add(event.identity)
            self.popups.notify(event.title, event.body, event.kind, self.prefs)
        if due:
            try:
                save_sent(self.settings, self.sent, now.date())
            except OSError:
                self._notice('تعذّر حفظ سجل التنبيهات؛ قد يتكرر آخر تنبيه بعد إعادة التشغيل.')
        if len(self.sent) > 45:
            self.sent = prune_sent(self.sent, now.date())

    def _test_notification(self, prefs=None, kind='prayer'):
        # Qt's QAction triggered signal passes a bool (checked); ignore it.
        if not isinstance(prefs, ReminderPrefs):
            prefs = self.prefs
        if kind == 'azkar':
            title, body = 'أذكار الصباح • تجربة', 'خذ لحظة للذكر والاستغفار. هذا إشعار تجريبي.'
        else:
            title, body = 'حان وقت الصلاة • تجربة', 'حان وقت صلاة الظهر. هذا إشعار تجريبي.'
        self.popups.notify(tr(title, prefs.language), tr(
            body, prefs.language), kind, prefs, preview=True)

    def _open_settings(self):
        if self._settings_dialog is not None:
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        def commit(conf, prefs):
            commit_preferences(self.settings, conf, prefs, self.startup)

        try:
            enabled = self.startup.enabled()
        except OSError as error:
            self._notice(str(error))
            return
        dialog = SettingsDialog(self.conf, self.prefs, self,
                                commit=commit, startup_enabled=enabled)
        self._settings_dialog = dialog
        dialog.preview_requested.connect(self._test_notification)
        try:
            accepted = dialog.exec() == dialog.DialogCode.Accepted
        finally:
            self._settings_dialog = None
            dialog.deleteLater()
        if not accepted:
            return
        new_conf, new_prefs = dialog.result_config, dialog.result_prefs
        if new_conf is None or new_prefs is None:
            return
        self.conf, self.prefs = new_conf, new_prefs
        self.popups.cancel_pending()
        self._rebuild_presentation()
        self._refresh()

    def _activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _stop_audio(self):
        self.popups.sound.stop()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _hide_to_tray(self):
        if self.tray_available:
            self.hide()
        else:
            QMessageBox.information(
                self, tr('العمل بالخلفية', self.prefs.language),
                tr('أيقونة شريط النظام غير متاحة حالياً، اترك النافذة مفتوحة للتذكيرات.',
                   self.prefs.language),
            )

    def closeEvent(self, event):
        if self.tray_available:
            event.ignore()
            self.hide()
        else:
            event.accept()
            QApplication.instance().quit()

    def _quit(self):
        self.clock.stop()
        self.popups.shutdown()
        self.tray.hide()
        QApplication.instance().quit()
