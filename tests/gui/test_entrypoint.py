"""Exercise the real entrypoint lock across isolated processes."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHILD = r'''
import sys
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
import prayerpal
folder = Path(sys.argv[1])
class FakeWindow:
    def show(self):
        (folder / 'ready').write_text('ready')
        print('WINDOW CREATED', flush=True)
        QTimer.singleShot(1200, QApplication.instance().quit)
with patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=str(folder)), \
     patch('biuret_prayerpal.main_window.MainWindow', FakeWindow), \
     patch('PySide6.QtWidgets.QMessageBox.information',
           side_effect=lambda *args: print('DUPLICATE REFUSED', flush=True)):
    raise SystemExit(prayerpal.main())
'''


class EntryPointTests(unittest.TestCase):
    def test_second_instance_is_refused_and_lock_released_after_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONIOENCODING='utf-8')
            command = [sys.executable, '-u', '-c', CHILD, directory]
            first = subprocess.Popen(command, cwd=ROOT, env=environment,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, encoding='utf-8', errors='replace')
            try:
                deadline = time.monotonic() + 5
                marker = Path(directory) / 'ready'
                while not marker.exists() and first.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), 'First isolated instance did not initialize')
                duplicate = subprocess.run(command, cwd=ROOT, env=environment,
                                           capture_output=True, text=True, timeout=5,
                                           encoding='utf-8', errors='replace')
                self.assertEqual(duplicate.returncode, 1, duplicate.stderr)
                self.assertIn('DUPLICATE REFUSED', duplicate.stdout)
                self.assertNotIn('WINDOW CREATED', duplicate.stdout)
                stdout, stderr = first.communicate(timeout=5)
                self.assertEqual(first.returncode, 0, stderr)
                self.assertIn('WINDOW CREATED', stdout)
            finally:
                if first.poll() is None:
                    first.kill()
                    first.communicate(timeout=5)
            restarted = subprocess.run(command, cwd=ROOT, env=environment,
                                       capture_output=True, text=True, timeout=5,
                                       encoding='utf-8', errors='replace')
            self.assertEqual(restarted.returncode, 0, restarted.stderr)
            self.assertIn('WINDOW CREATED', restarted.stdout)
