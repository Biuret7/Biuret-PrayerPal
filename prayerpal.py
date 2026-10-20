"""Biuret PrayerPal 4 — compact Windows desktop entrypoint.

Run: py -m pip install -r requirements.txt && py prayerpal.py
Tests: py prayerpal.py --self-test   (does not require GUI libraries)
"""
import sys


def main():
    if '--packaging-smoke-test' in sys.argv:
        from biuret_prayerpal.packaging_smoke import run_smoke
        index = sys.argv.index('--packaging-smoke-test')
        if index + 1 >= len(sys.argv):
            return 2
        report_file = sys.argv[index + 1]
        try:
            return run_smoke(report_file)
        except Exception as error:
            # Diagnostic mode must report an import failure without opening a
            # bootloader error dialog that would block an unattended build.
            import json
            from pathlib import Path
            Path(report_file).write_text(json.dumps({
                'passed': False, 'frozen': bool(getattr(sys, 'frozen', False)),
                'error': str(error),
            }), encoding='utf-8')
            return 1
    if '--self-test' in sys.argv:
        if getattr(sys, 'frozen', False):
            # Source tests are intentionally not shipped in the executable.
            return 2
        import unittest
        from pathlib import Path
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent / 'tests'))
        outcome = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if outcome.wasSuccessful() else 1
    try:
        from PySide6.QtCore import QLockFile, QStandardPaths
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError as error:
        print('PySide6 غير مثبتة في نفس بيئة Python. ثبّتها بالأمر:')
        print('py -m pip install -r requirements.txt')
        print(error)
        return 1
    from biuret_prayerpal.main_window import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName('Biuret PrayerPal')
    from biuret_prayerpal.core import APP_VERSION
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName('Biuret')
    app.setFont(QFont('Segoe UI', 10))
    app.setQuitOnLastWindowClosed(False)
    from pathlib import Path
    try:
        data = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation))
        data.mkdir(parents=True, exist_ok=True)
        instance_lock = QLockFile(str(data / 'prayerpal.lock'))
        instance_lock.setStaleLockTime(0)
        if not instance_lock.tryLock(0):
            QMessageBox.information(
                None, 'Biuret PrayerPal',
                'التطبيق قيد التشغيل بالفعل أو تعذّر قفل مجلد البيانات. '
                'تحقق من أيقونة شريط النظام.',
            )
            return 1
    except OSError:
        QMessageBox.critical(None, 'Biuret PrayerPal', 'تعذّر فتح مجلد بيانات التطبيق للكتابة.')
        return 1
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
