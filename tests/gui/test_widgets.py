"""Real Qt widgets and media service tests; all settings/audio are isolated.

Run separately: python -m unittest discover -s tests/gui -v
The tests do not access the user's PrayerPal registry settings or play audible audio.
"""
import os
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

try:
    from PySide6.QtCore import QObject, QSettings, Qt, Signal, QEvent, QPoint
    from PySide6.QtGui import QFont, QFontDatabase, QFocusEvent, QColor
    from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (
        QApplication, QLabel, QMessageBox, QWidget, QAbstractButton, QComboBox, QAbstractSpinBox,
    )
    from biuret_prayerpal.storage import load_core, load_reminders, save_preferences
    from biuret_prayerpal.sound import SoundService
    from biuret_prayerpal.preferences import ANIMATIONS, POSITIONS, ReminderPrefs
    from biuret_prayerpal.popup import PopupManager, Toast
    from biuret_prayerpal.main_window import MainWindow
    from biuret_prayerpal.dialogs import SettingsDialog
    from biuret_prayerpal.core import Config
except ImportError as error:
    if (error.name or '').startswith('PySide6'):
        raise unittest.SkipTest('PySide6 is required for the separate GUI suite') from error
    raise

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


class FakeSound(QObject):
    error_message = Signal(str)

    def __init__(self):
        super().__init__()
        self.plays = []
        self.stops = []

    def play(self, prefs, kind):
        self.plays.append((prefs, kind))
        return len(self.plays)

    def stop(self, token=None):
        self.stops.append(token)


class QtRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        # The offscreen Windows plugin does not enumerate system fonts.
        if not QFontDatabase.families():
            for name in ('segoeui.ttf', 'seguisb.ttf', 'consola.ttf', 'seguisym.ttf'):
                QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR', 'C:/Windows'))
                                                     / 'Fonts' / name))
        cls.app.setFont(QFont('Segoe UI', 10))
        cls.qt_exceptions = []
        cls.old_excepthook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: cls.qt_exceptions.append(value)

    @classmethod
    def tearDownClass(cls):
        sys.excepthook = cls.old_excepthook

    def setUp(self):
        self.objects = []
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.qt_exceptions.clear()

    def tearDown(self):
        for obj in reversed(self.objects):
            if isinstance(obj, MainWindow):
                obj.clock.stop()
                obj.popups.shutdown()
                obj.tray.hide()
                obj.hide()
            elif isinstance(obj, PopupManager):
                obj.shutdown()
            elif isinstance(obj, Toast):
                obj.discard()
                continue
            elif isinstance(obj, SoundService):
                obj.stop()
            elif isinstance(obj, SettingsDialog):
                obj.hide()
            obj.deleteLater()
        QTest.qWait(10)
        self.assertEqual(self.qt_exceptions, [], 'Uncaught exception in a Qt slot/event')

    def keep(self, obj):
        self.objects.append(obj)
        return obj

    def dialog(self, prefs=None, commit=None):
        return self.keep(SettingsDialog(Config(city='My city'), prefs or ReminderPrefs(muted=True),
                                        commit=commit))

    def manager(self):
        return self.keep(PopupManager(sound=FakeSound()))

    def settings(self):
        return QSettings(str(self.directory / 'preferences.ini'), QSettings.Format.IniFormat)

    def test_unsaved_test_button_uses_every_current_control(self):
        dialog = self.dialog()
        previews = []
        dialog.preview_requested.connect(lambda prefs, kind: previews.append((prefs, kind)))
        dialog.position.setCurrentIndex(dialog.position.findData('top_left'))
        dialog.animation.setCurrentIndex(dialog.animation.findData('zoom'))
        dialog.volume.setValue(23)
        dialog.accent.setText('#C8AA66')
        dialog.sound.setCurrentIndex(dialog.sound.findData('adhan'))
        dialog.adhan_file.setText(str(self.directory / 'selected.wav'))
        dialog.reduced_motion.setChecked(True)
        dialog.preview_kind.setCurrentIndex(1)
        dialog.test_button.click()
        prefs, kind = previews[0]
        self.assertEqual((prefs.position, prefs.animation, prefs.volume, prefs.accent, kind),
                         ('top_left', 'zoom', 23, '#C8AA66', 'azkar'))
        self.assertTrue(prefs.reduced_motion)
        self.assertEqual(prefs.adhan_file, str(self.directory / 'selected.wav'))
        self.assertIsNone(dialog.result_prefs)

    def test_failed_commit_keeps_dialog_open_and_edits_available(self):
        def fail(conf, prefs):
            raise OSError('simulated disk failure')
        dialog = self.dialog(commit=fail)
        dialog.show()
        dialog.city.setCurrentText('Edited city')
        with patch.object(QMessageBox, 'warning') as warning:
            dialog.save()
        warning.assert_called_once()
        self.assertTrue(dialog.isVisible())
        self.assertEqual(dialog.city.currentText(), 'Edited city')
        self.assertIsNone(dialog.result_config)
        self.assertFalse(dialog._closing)

    def test_save_persists_custom_city_and_time_format_together(self):
        settings = self.settings()
        dialog = self.dialog(ReminderPrefs(muted=True, reduced_motion=True),
                             commit=lambda conf, prefs: save_preferences(settings, conf, prefs))
        dialog.time_24.setChecked(False)
        dialog.city.setCurrentText('My custom city')
        dialog.position.setCurrentIndex(dialog.position.findData('center'))
        dialog.save()
        reopened = self.settings()
        self.assertEqual(load_core(reopened).city, 'My custom city')
        self.assertFalse(load_core(reopened).time_24)
        self.assertEqual(load_reminders(reopened).position, 'center')
        self.assertEqual(dialog.result(), SettingsDialog.DialogCode.Accepted)

    def test_escape_fades_out_and_emits_one_rejection(self):
        dialog = self.dialog()
        rejected = []
        dialog.rejected.connect(lambda: rejected.append(True))
        dialog.show()
        QTest.qWait(280)
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        QTest.qWait(190)
        self.assertFalse(dialog.isVisible())
        self.assertEqual(rejected, [True])

    def test_popup_all_positions_and_styles_keep_constant_layout_size(self):
        for position in POSITIONS:
            for animation in ANIMATIONS:
                with self.subTest(position=position, animation=animation):
                    prefs = ReminderPrefs(position=position, animation=animation, muted=True)
                    toast = Toast('حان وقت الصلاة', 'تجربة إشعار', prefs)
                    toast.display()
                    target = toast._target
                    self.assertEqual(toast.size(), target.size())
                    toast._group.setCurrentTime(toast._group.duration() // 2)
                    self.assertEqual(toast.size(), target.size())
                    toast._group.setCurrentTime(toast._group.duration())
                    self.assertEqual(toast.geometry(), target)
                    self.assertTrue(toast._timer.isActive())
                    toast.discard()
        QTest.qWait(10)

    def test_popup_renders_message_as_plain_text(self):
        toast = self.keep(Toast('<b>title</b>', '<img src="remote">', ReminderPrefs(muted=True)))
        for label in toast.findChildren(QLabel):
            if label.objectName() in ('headline', 'body'):
                self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText)

    def test_zoom_frame_and_final_halo_keep_transparent_edges(self):
        toast = self.keep(Toast('حان وقت الصلاة', 'تجربة إشعار',
                                ReminderPrefs(animation='zoom', muted=True)))
        toast.display()
        toast._group.setCurrentTime(toast._group.duration() // 2)
        toast._group.setCurrentTime(toast._group.duration())
        image = toast.grab().toImage()
        self.assertEqual(image.pixelColor(0, image.height() // 2).alpha(), 0)
        self.assertLess(image.pixelColor(10, image.height() // 2).alpha(), 60)

    def test_previews_preserve_pending_and_interrupted_real_alerts(self):
        manager = self.manager()
        prefs = ReminderPrefs(muted=True, reduced_motion=True)
        manager.notify('real one', 'body', 'prayer', prefs)
        old = manager.current
        manager.notify('real two', 'body', 'prayer', prefs)
        manager.notify('preview', 'body', 'azkar', prefs, preview=True)
        self.assertEqual([item[0] for item in manager.queue], ['real one', 'real two'])
        current = manager.current
        old.closed.emit(True)  # Delayed old callback must not affect current ownership.
        self.assertIs(manager.current, current)
        current.close_animated(manual=True)
        self.assertEqual(manager._request[0], 'real one')
        manager.current.close_animated(manual=True)
        self.assertEqual(manager._request[0], 'real two')

    def test_repeated_previews_do_not_accumulate_or_restart_real_queue(self):
        manager = self.manager()
        prefs = ReminderPrefs(muted=True, reduced_motion=True)
        manager.notify('real', 'body', 'prayer', prefs)
        for number in range(20):
            manager.notify(f'preview {number}', 'body', 'prayer', prefs, preview=True)
        self.assertEqual([item[0] for item in manager.queue], ['real'])
        self.assertEqual(manager._request[0], 'preview 19')
        manager.cancel_pending()
        self.assertIsNone(manager.current)
        self.assertFalse(manager.queue)

    def test_shutdown_stops_timers_and_cannot_advance_queued_alert(self):
        manager = self.manager()
        prefs = ReminderPrefs(muted=True)
        manager.notify('one', 'body', 'prayer', prefs)
        manager.notify('two', 'body', 'prayer', prefs)
        old = manager.current
        manager.shutdown()
        old.closed.emit(False)
        manager.notify('three', 'body', 'prayer', prefs)
        self.assertIsNone(manager.current)
        self.assertFalse(manager.queue)
        self.assertEqual(len(manager.sound.plays), 1)

    def test_automatic_dismissal_keeps_recording_manual_dismissal_stops_it(self):
        manager = self.manager()
        prefs = ReminderPrefs(muted=True, reduced_motion=True)
        manager.notify('one', 'body', 'prayer', prefs)
        manager.current.close_animated(manual=False)
        self.assertEqual(manager.sound.stops, [])
        manager.notify('two', 'body', 'prayer', prefs)
        manager.current.close_animated(manual=True)
        self.assertEqual(manager.sound.stops, [2])

    def test_audio_stale_stop_and_stale_error_cannot_affect_new_request(self):
        service = self.keep(SoundService(chime_path=self.directory / 'chime.wav'))
        errors = []
        service.error_message.connect(errors.append)
        first = service.play(ReminderPrefs(muted=True), 'prayer')
        second = service.play(ReminderPrefs(muted=True), 'prayer')
        service.stop(first)
        self.assertEqual(service._generation, second)
        service._on_error(first, QMediaPlayer.Error.ResourceError, 'stale error')
        self.assertEqual(errors, [])
        service._on_error(second, QMediaPlayer.Error.ResourceError, 'current error')
        self.assertEqual(len(errors), 1)

    def test_worker_thread_cannot_mutate_qt_audio_or_popup_objects(self):
        service = self.keep(SoundService(chime_path=self.directory / 'chime.wav'))
        manager = self.manager()
        prefs = ReminderPrefs(muted=True)
        with ThreadPoolExecutor(max_workers=1) as worker:
            operations = (
                lambda: service.play(prefs, 'prayer'),
                lambda: manager.notify('title', 'body', 'prayer', prefs),
            )
            for operation in operations:
                with self.assertRaises(RuntimeError):
                    worker.submit(operation).result(timeout=3)

    def test_audio_missing_file_reports_failure_without_crashing(self):
        service = self.keep(SoundService(chime_path=self.directory / 'chime.wav'))
        errors = []
        service.error_message.connect(errors.append)
        prefs = ReminderPrefs(sound_mode='adhan',
                              adhan_file=str(self.directory / 'missing.wav'))
        service.play(prefs, 'prayer')
        self.assertEqual(len(errors), 1)
        self.assertIsNone(service.player)

    def test_audio_volume_mute_and_playback_state_match_controls(self):
        service = self.keep(SoundService(chime_path=self.directory / 'chime.wav'))
        changes = []
        service.active_changed.connect(changes.append)
        service.output.setMuted(True)  # Keep the test inaudible independently of app preferences.
        token = service.play(ReminderPrefs(volume=23), 'prayer')
        self.assertAlmostEqual(service.output.volume(), 0.23, places=4)
        service._on_state(token, QMediaPlayer.PlaybackState.PlayingState)
        self.assertTrue(service._active)
        service.play(ReminderPrefs(muted=True), 'prayer')
        self.assertIsNone(service.player)
        self.assertFalse(service._active)
        self.assertEqual(changes[-1], False)

    def test_real_chime_decodes_to_end_with_output_muted(self):
        if not QMediaDevices.audioOutputs():
            self.skipTest('No audio output device is available for the media backend')
        service = self.keep(SoundService(chime_path=self.directory / 'chime.wav'))
        errors = []
        service.error_message.connect(errors.append)
        service.output.setMuted(True)
        service.play(ReminderPrefs(), 'prayer')
        player = service.player
        for _ in range(100):
            if errors or player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
                break
            QTest.qWait(30)
        self.assertEqual(errors, [])
        self.assertEqual(player.mediaStatus(), QMediaPlayer.MediaStatus.EndOfMedia)

    def test_bundled_adhan_plays_without_a_user_file(self):
        service = self.keep(SoundService(chime_path=self.directory / 'chime.wav'))
        errors = []
        service.error_message.connect(errors.append)
        service.output.setMuted(True)
        service.play(ReminderPrefs(sound_mode='bundled_adhan', adhan_file=''), 'prayer')
        self.assertIsNotNone(service.player)
        deadline = time.monotonic() + 4
        while not errors and service.player.position() < 150 and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(service.player.position(), 150)
        self.assertTrue(service.player.source().toLocalFile().endswith(
            'assets/sounds/adhan-omar-hisham-al-arabi.mp3'))

    def test_button_hover_press_and_focus_do_not_move_layout(self):
        dialog = self.dialog()
        dialog.show()
        QTest.qWait(280)
        button = dialog.test_button
        before = button.geometry()
        button.setFocus()
        QTest.mouseMove(button, button.rect().center())
        QTest.mousePress(button, Qt.MouseButton.LeftButton)
        QTest.qWait(170)
        self.assertEqual(button.geometry(), before)
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton)
        # Native timer delivery can finish just after a fixed 170 ms sleep.
        # Await completion under a deadline while retaining the exact end-state
        # and geometry assertions.
        deadline = time.monotonic() + 1
        while button._press.state() == button._press.State.Running and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertEqual(button._press.state(), button._press.State.Stopped)
        self.assertEqual(button.geometry(), before)
        self.assertGreater(button._progress, 0.9)
        self.assertAlmostEqual(button._scale, 1.0)

    def test_main_window_theme_failure_does_not_apply_unpersisted_theme(self):
        settings = self.settings()
        save_preferences(settings, Config(), ReminderPrefs(enabled=False, muted=True))
        with patch('biuret_prayerpal.main_window.QSystemTrayIcon.isSystemTrayAvailable',
                   return_value=False):
            window = self.keep(MainWindow(settings))
        window.clock.stop()
        original = window.conf.dark
        with patch('biuret_prayerpal.main_window.save_preferences',
                   side_effect=OSError('disk failure')):
            window._toggle_theme()
        self.assertEqual(window.conf.dark, original)
        self.assertEqual(window.property('darkTheme'), original)

    def test_calculation_failure_keeps_azkar_without_recalculating_each_tick(self):
        settings = self.settings()
        save_preferences(settings, Config(), ReminderPrefs(enabled=False, muted=True))
        with patch('biuret_prayerpal.main_window.QSystemTrayIcon.isSystemTrayAvailable',
                   return_value=False):
            window = self.keep(MainWindow(settings))
        window.clock.stop()
        window.prefs = ReminderPrefs(morning_azkar=True, muted=True)
        with patch('biuret_prayerpal.main_window.calculate_day',
                   side_effect=ValueError('simulated polar day')) as calculate:
            window._refresh()
            window._tick()
            window._tick()
        self.assertEqual(calculate.call_count, 1)
        self.assertEqual(len(window.events), 1)
        self.assertEqual(window.events[0].kind, 'azkar')

    def main_window(self, language='ar', reduced_motion=False):
        settings = self.settings()
        save_preferences(settings, Config(), ReminderPrefs(
            enabled=False, muted=True, language=language, reduced_motion=reduced_motion))
        window = self.keep(MainWindow(settings, enable_tray=False))
        window.clock.stop()
        return window

    def test_mouse_click_clears_focus_border_but_keyboard_navigation_retains_it(self):
        dialog = self.dialog(ReminderPrefs(muted=True, reduced_motion=True))
        dialog.show()
        button = dialog.test_button
        before = button.geometry()
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
        self.assertFalse(button._keyboard_focus)
        self.assertEqual(button._progress, 0)
        QApplication.sendEvent(button, QFocusEvent(QEvent.Type.FocusIn,
                                                   Qt.FocusReason.TabFocusReason))
        self.assertTrue(button._keyboard_focus)
        self.assertEqual(button._progress, 1)
        QTest.mousePress(button, Qt.MouseButton.LeftButton)
        button.setEnabled(False)
        self.assertEqual(button._scale, 1)
        self.assertEqual(button.geometry(), before)

    def test_theme_animation_intermediate_rapid_toggle_and_reduced_motion(self):
        window = self.main_window()
        window.show()
        QTest.qWait(30)
        geometry = window.theme.geometry()
        window._toggle_theme()
        window.theme._theme_animation.setCurrentTime(140)
        self.assertGreater(window.theme._theme_progress, 0)
        self.assertLess(window.theme._theme_progress, 1)
        self.assertIsNotNone(window._theme_overlay)
        for _ in range(5):
            window._toggle_theme()
        QTest.qWait(350)
        self.assertIsNone(window._theme_overlay)
        self.assertEqual(window.theme.geometry(), geometry)
        self.assertEqual(window.theme._theme_progress, float(window.conf.dark))
        self.assertEqual(load_core(window.settings).dark, window.conf.dark)
        window.prefs = replace(window.prefs, reduced_motion=True)
        window._apply_theme()
        window._toggle_theme()
        self.assertIsNone(window._theme_overlay)
        self.assertEqual(window.theme._theme_progress, float(window.conf.dark))

    def test_language_toggle_preserves_services_sent_state_and_persists(self):
        window = self.main_window()
        services = window.popups, window.clock
        sent = {'2026-10-20:Fajr:prayer'}
        window.sent = sent.copy()
        window._toggle_language()
        self.assertEqual(window.prefs.language, 'en')
        self.assertEqual(window.layoutDirection(), Qt.LayoutDirection.LeftToRight)
        self.assertEqual(window.language_button.text(), 'AR')
        self.assertEqual(load_reminders(window.settings).language, 'en')
        self.assertEqual((window.popups, window.clock), services)
        self.assertTrue(any(a.text() == 'Settings' for a in window.tray.contextMenu().actions()))
        self.assertEqual(window.sent, sent)
        window._toggle_language()
        self.assertEqual(window.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self.assertEqual(window.language_button.text(), 'EN')

    def test_english_settings_have_translated_labels_and_preserve_canonical_city(self):
        from biuret_prayerpal.i18n import tr
        dialog = self.keep(SettingsDialog(Config(), ReminderPrefs(language='en', muted=True)))
        self.assertEqual(dialog.tabs.count(), 6)
        self.assertEqual([dialog.tabs.tabText(i) for i in range(6)],
                         ['Location', 'Calculation', 'Reminders', 'Sound', 'Popup', 'App'])
        self.assertEqual(dialog._collect_config().city, Config().city)
        for widget in dialog.findChildren(QWidget):
            texts = [widget.toolTip(), widget.accessibleName()]
            if isinstance(widget, (QLabel, QAbstractButton)):
                texts.append(widget.text())
            if isinstance(widget, QComboBox):
                texts.extend(widget.itemText(i) for i in range(widget.count()))
            for text in texts:
                if text != 'العربية':  # Language endonym must remain recognisable.
                    self.assertFalse(any('\u0600' <= char <= '\u06ff' for char in text), text)
        dialog.city.setCurrentIndex(dialog.city.findData('رام الله'))
        self.assertEqual(dialog.city.currentText(), tr('رام الله', 'en'))
        self.assertEqual(dialog._collect_config().city, 'رام الله')
        dialog.city.setEditText('My مدينة')
        self.assertEqual(dialog._collect_config().city, 'My مدينة')
        dialog.interface_language.setCurrentIndex(0)
        self.assertEqual(dialog._collect_prefs().language, 'ar')

    def test_cancel_does_not_commit_startup_and_preview_uses_selected_language(self):
        calls = []
        dialog = self.dialog(commit=lambda conf, prefs: calls.append(prefs))
        previews = []
        dialog.preview_requested.connect(lambda prefs, kind: previews.append(prefs))
        dialog.start_on_login.setChecked(True)
        dialog.interface_language.setCurrentIndex(1)
        dialog.preview()
        self.assertEqual(previews[0].language, 'en')
        dialog.reject()
        self.assertEqual(calls, [])

    def test_sunrise_is_explicit_today_information_and_stop_only_while_playing(self):
        window = self.main_window(language='en')
        day = window.day_loaded
        evening = datetime.combine(day, datetime.min.time(),
                                   tzinfo=window.conf.zone).replace(hour=23)
        with patch('biuret_prayerpal.main_window.datetime') as clock:
            clock.now.return_value = evening
            window._tick()
        self.assertEqual(window.current_prayer.text(), 'Current prayer: Isha')
        self.assertTrue(window.sunrise.text().startswith('Sunrise today: '))
        self.assertEqual(window.audio_stack.currentWidget(), window.audio_idle)
        self.assertFalse(window.stop_audio_button.isEnabled())
        window._audio_state_changed(True)
        self.assertEqual(window.audio_stack.currentWidget(), window.stop_audio_button)
        self.assertTrue(window.stop_audio_button.isEnabled())
        with patch.object(window.popups.sound, 'stop') as stop:
            window.stop_audio_button.click()
        stop.assert_called_once()
        window._audio_state_changed(False)
        self.assertEqual(window.audio_stack.currentWidget(), window.audio_idle)

    def test_all_settings_tabs_have_clear_rounded_corners_in_both_themes(self):
        from biuret_prayerpal.theme import PALETTES
        for dark in (True, False):
            dialog = self.keep(SettingsDialog(Config(dark=dark),
                                              ReminderPrefs(muted=True, reduced_motion=True)))
            dialog.show()
            for index in range(dialog.tabs.count()):
                dialog.tabs.setCurrentIndex(index)
                QTest.qWait(10)
                scroll = dialog.tabs.widget(index)
                for surface in (scroll, scroll.viewport(), scroll.widget()):
                    self.assertFalse(surface.autoFillBackground())
                image = dialog.grab().toImage()
                ratio = image.devicePixelRatio()
                # A square viewport overlay would fill this bottom pane corner.
                for x in (1, dialog.tabs.width() - 2):
                    corner = dialog.tabs.mapTo(dialog, QPoint(x, dialog.tabs.height() - 2))
                    color = image.pixelColor(int(corner.x() * ratio), int(corner.y() * ratio))
                    self.assertEqual(color, QColor(PALETTES[dark]['bg']))

    def test_numeric_and_time_editors_remain_readable_in_both_languages_and_themes(self):
        for dark in (True, False):
            for language in ('ar', 'en'):
                dialog = self.keep(SettingsDialog(Config(dark=dark), ReminderPrefs(
                    language=language, muted=True, reduced_motion=True)))
                dialog.show()
                for index in range(dialog.tabs.count()):
                    dialog.tabs.setCurrentIndex(index)
                    QTest.qWait(10)
                    for control in dialog.tabs.widget(index).findChildren(QAbstractSpinBox):
                        editor = control.lineEdit()
                        self.assertTrue(editor.isVisible())
                        self.assertTrue(editor.text())
                        self.assertGreaterEqual(editor.width(), control.width() * 0.8)
                        self.assertTrue(control.rect().contains(editor.geometry()))
                dialog.tabs.setCurrentIndex(1)
                previous = dialog.fajr.value()
                QTest.keyClick(dialog.fajr, Qt.Key.Key_Up)
                self.assertGreater(dialog.fajr.value(), previous)

    def test_duration_mouse_typing_limits_preview_timer_and_persistence(self):
        for dark in (True, False):
            for language in ('ar', 'en'):
                with self.subTest(dark=dark, language=language):
                    settings = QSettings(str(self.directory / f'{dark}-{language}.ini'),
                                         QSettings.Format.IniFormat)
                    prefs = ReminderPrefs(language=language, duration_seconds=20,
                                          reduced_motion=True, muted=True)

                    def commit(conf, prefs):
                        save_preferences(settings, conf, prefs)
                    dialog = self.keep(SettingsDialog(Config(dark=dark), prefs, commit=commit))
                    dialog.show()
                    dialog.tabs.setCurrentIndex(2)
                    QTest.qWait(20)
                    self.assertTrue(dialog.duration_increase.isVisible())
                    self.assertTrue(dialog.duration_decrease.isVisible())
                    QTest.mouseClick(dialog.duration_increase, Qt.MouseButton.LeftButton)
                    self.assertEqual(dialog.duration.value(), 21)
                    QTest.mouseClick(dialog.duration_decrease, Qt.MouseButton.LeftButton)
                    self.assertEqual(dialog.duration.value(), 20)
                    dialog.duration.setFocus()
                    QTest.keyClick(dialog.duration, Qt.Key.Key_A,
                                   Qt.KeyboardModifier.ControlModifier)
                    QTest.keyClicks(dialog.duration, '15')
                    QTest.keyClick(dialog.duration, Qt.Key.Key_Tab)
                    self.assertEqual(dialog.duration.value(), 15)
                    for boundary, button in ((4, dialog.duration_decrease),
                                             (30, dialog.duration_increase)):
                        dialog.duration.setValue(boundary)
                        self.assertFalse(button.isEnabled())
                        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                        self.assertEqual(dialog.duration.value(), boundary)
                    previews = []
                    dialog.preview_requested.connect(lambda prefs, kind: previews.append(prefs))
                    QTest.mouseClick(dialog.test_button, Qt.MouseButton.LeftButton)
                    self.assertEqual(previews[0].duration_seconds, 30)
                    toast = Toast('Preview', 'Duration check', previews[0])
                    try:
                        toast.display()
                        self.assertTrue(toast._timer.isActive())
                        self.assertEqual(toast._timer.interval(), 30000)
                    finally:
                        toast.discard()
                    dialog.save()
                    self.assertEqual(dialog.result(), SettingsDialog.DialogCode.Accepted)
                    restored = load_reminders(settings)
                    self.assertEqual(restored.duration_seconds, 30)
                    reopened = self.keep(SettingsDialog(load_core(settings), restored))
                    self.assertEqual(reopened.duration.value(), 30)
