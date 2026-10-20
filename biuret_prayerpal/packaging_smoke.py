"""Opt-in frozen-build verification; never reads the user's saved settings."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo


def run_smoke(report_file: str) -> int:
    from PySide6.QtCore import QSettings, QTimer
    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtWidgets import QApplication
    from .core import Config, calculate_day
    from .dialogs import SettingsDialog
    from .main_window import MainWindow
    from .preferences import ReminderPrefs
    from .resources import resource_path
    from .sound import SoundService
    from .storage import save_preferences

    report_path = Path(report_file).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    results = {'frozen': bool(getattr(sys, 'frozen', False)), 'passed': False, 'checks': {}}
    app = QApplication([])
    app.setApplicationName('Biuret PrayerPal Packaging Check')
    app.setOrganizationName('Biuret')
    app.setQuitOnLastWindowClosed(False)
    exit_code = 1
    old_excepthook = sys.excepthook
    state = {'finished': False}

    def finish(passed, error=None):
        nonlocal exit_code
        if state['finished']:
            return
        state['finished'] = True
        watchdog.stop()
        results['passed'] = passed and results['frozen']
        if error:
            results['error'] = str(error)
        report_path.write_text(json.dumps(results, indent=2), encoding='utf-8')
        exit_code = 0 if results['passed'] else 1
        app.quit()

    sys.excepthook = lambda kind, value, traceback: finish(False, value)
    watchdog = QTimer()
    watchdog.setSingleShot(True)
    watchdog.timeout.connect(lambda: finish(False, 'GUI/audio smoke check exceeded 8 seconds'))
    watchdog.start(8000)
    temporary = tempfile.TemporaryDirectory(prefix='prayerpal-smoke-', dir=report_path.parent)
    try:
        assets = [resource_path('icon.ico'), resource_path('assets/sounds/chime.wav'),
                  resource_path('assets/sounds/adhan-omar-hisham-al-arabi.mp3')]
        if not all(path.is_file() for path in assets):
            raise OSError('A required bundled asset is missing')
        results['checks']['assets'] = True
        config = Config()
        config.zone  # Resolve the application's default bundled timezone.
        ZoneInfo('America/New_York')
        from datetime import date
        calculate_day(date(2026, 10, 20), config)
        results['checks']['timezone_and_calculation'] = True
        settings = QSettings(str(Path(temporary.name) / 'settings.ini'),
                             QSettings.Format.IniFormat)
        save_preferences(settings, config, ReminderPrefs(enabled=False, muted=True))
        window = MainWindow(settings, enable_tray=False)
        window.clock.stop()
        window.show()
        results['checks']['window_icon'] = not window.windowIcon().isNull()
        dialog = SettingsDialog(config, ReminderPrefs(muted=True, reduced_motion=True), window)
        previews = []
        dialog.preview_requested.connect(lambda prefs, kind: previews.append(prefs))
        dialog.test_button.click()
        results['checks']['settings_preview'] = len(previews) == 1
        dialog.deleteLater()
        sound = SoundService()
        sound.output.setMuted(True)
        sound.error_message.connect(lambda message: finish(False, message))

        def media_status(status):
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                results['checks']['native_media_end_of_file_muted'] = True
                QTimer.singleShot(0, start_adhan)

        def adhan_position(position):
            if position >= 150:
                results['checks']['bundled_adhan_mp3_playback_muted'] = True
                results['checks']['qt_window_visible'] = window.isVisible()
                finish(all(results['checks'].values()))

        def start_adhan():
            sound.play(ReminderPrefs(sound_mode='bundled_adhan', volume=20), 'prayer')
            if sound.player is None:
                finish(False, 'Bundled Adhan did not start')
            else:
                sound.player.positionChanged.connect(adhan_position)

        def start_audio():
            sound.play(ReminderPrefs(volume=20), 'prayer')
            if sound.player is None:
                finish(False, 'Media player did not start')
            else:
                sound.player.mediaStatusChanged.connect(media_status)

        QTimer.singleShot(300, start_audio)
        app.exec()
        sound.stop()
        window.popups.shutdown()
        window.hide()
    except (OSError, ValueError, RuntimeError) as error:
        finish(False, error)
    finally:
        temporary.cleanup()
        sys.excepthook = old_excepthook
    return exit_code
