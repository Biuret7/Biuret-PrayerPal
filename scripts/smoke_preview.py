"""Render reproducible screenshots using isolated settings and muted reminders.

Run from any directory: python scripts/smoke_preview.py [--native]
Offscreen mode renders widgets without opening desktop windows.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='Use the native Windows Qt platform')
    arguments = parser.parse_args()
    os.environ['QT_QPA_PLATFORM'] = 'windows' if arguments.native else 'offscreen'
    sys.path.insert(0, str(ROOT))

    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from biuret_prayerpal.core import Config
    from biuret_prayerpal.dialogs import SettingsDialog
    from biuret_prayerpal.main_window import MainWindow
    from biuret_prayerpal.popup import Toast
    from biuret_prayerpal.preferences import ReminderPrefs
    from biuret_prayerpal.storage import save_preferences

    app = QApplication([])
    if not QFontDatabase.families():
        for font in ('segoeui.ttf', 'seguisb.ttf', 'segoeuib.ttf',
                     'seguisym.ttf', 'consola.ttf', 'tahoma.ttf'):
            QFontDatabase.addApplicationFont(
                str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font))
    app.setFont(QFont('Segoe UI', 10))
    app.setQuitOnLastWindowClosed(False)
    temporary_root = ROOT / '.test-tmp'
    temporary_root.mkdir(exist_ok=True)
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    suffix = '-native' if arguments.native else ''

    def capture(widget, name):
        pixels = widget.grab()
        if name.startswith('popup'):
            # Render the translucent toast over the app surface for PNG viewers
            # that otherwise display transparent RGB channels at full opacity.
            surface = QPixmap(pixels.size())
            surface.setDevicePixelRatio(pixels.devicePixelRatio())
            surface.fill(QColor('#0B1018'))
            painter = QPainter(surface)
            painter.drawPixmap(0, 0, pixels)
            painter.end()
            pixels = surface
        if not pixels.save(str(output / f'{name}{suffix}.png')):
            raise OSError(f'Could not save screenshot: {name}')

    with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
        settings = QSettings(str(Path(directory) / 'settings.ini'), QSettings.Format.IniFormat)
        save_preferences(settings, Config(), ReminderPrefs(
            enabled=False, muted=True, sound_mode='bundled_adhan'))
        with patch('biuret_prayerpal.main_window.QSystemTrayIcon.isSystemTrayAvailable',
                   return_value=False):
            window = MainWindow(settings)
        window.clock.stop()
        window.show()
        QTest.qWait(300)
        capture(window, 'main-dark')
        window.conf = replace(window.conf, dark=False)
        window._apply_theme()
        QTest.qWait(30)
        capture(window, 'main-light')
        window.conf = replace(window.conf, dark=True)
        window._apply_theme()

        dialog = SettingsDialog(window.conf, window.prefs, window)
        dialog.resize(680, 720)
        dialog.show()
        QTest.qWait(280)
        tabs = ('location', 'calculation', 'reminders', 'sound', 'popup', 'app')
        for index, name in enumerate(tabs):
            dialog.tabs.setCurrentIndex(index)
            QTest.qWait(30)
            capture(dialog, f'settings-{name}')
        dialog.reject()
        QTest.qWait(180)
        toast = Toast('حان وقت الصلاة', 'حان الآن وقت صلاة الظهر. تقبّل الله طاعتكم.',
                      ReminderPrefs(animation='zoom', muted=True))
        toast.display()
        QTest.qWait(300)
        capture(toast, 'popup')
        toast.discard()
        window._toggle_language()
        QTest.qWait(30)
        capture(window, 'main-dark-en')
        window._toggle_theme()
        QTest.qWait(350)
        capture(window, 'main-light-en')
        dialog = SettingsDialog(window.conf, window.prefs, window)
        dialog.show()
        QTest.qWait(280)
        for index, name in enumerate(tabs):
            dialog.tabs.setCurrentIndex(index)
            QTest.qWait(30)
            capture(dialog, f'settings-{name}-en-light')
        dialog.reject()
        QTest.qWait(180)
        toast = Toast('Time for prayer', 'It is time for Dhuhr. May your prayers be accepted.',
                      ReminderPrefs(language='en', animation='zoom', muted=True))
        toast.display()
        QTest.qWait(300)
        capture(toast, 'popup-en')
        toast.discard()
        window._quit()
    print(f'UI screenshots saved to {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
