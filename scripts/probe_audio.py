"""Compare Qt media backends in isolated, muted subprocesses with a hard deadline."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = '''
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from biuret_prayerpal.sound import SoundService
from biuret_prayerpal.preferences import ReminderPrefs
app = QApplication([])
print('app ready', flush=True)
service = SoundService(chime_path=Path('artifacts/chime-test.wav').resolve())
service.output.setMuted(True)
print('service ready', flush=True)
service.error_message.connect(lambda message: print('error:', message, flush=True))
service.play(ReminderPrefs(), 'prayer')
print('play returned', flush=True)
for index in range(60):
    QTest.qWait(50)
    if index % 10 == 0:
        print('status', service.player.mediaStatus(), flush=True)
service.stop()
print('stopped', flush=True)
'''


def text(value):
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''


def main():
    (ROOT / 'artifacts').mkdir(exist_ok=True)
    outcomes = []
    for backend in ('ffmpeg', 'windows'):
        environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_MEDIA_BACKEND=backend,
                           QT_FFMPEG_DECODING_HW_DEVICE_TYPES=',',
                           QT_FFMPEG_ENCODING_HW_DEVICE_TYPES=',')
        print('BACKEND:', backend, flush=True)
        try:
            result = subprocess.run([sys.executable, '-u', '-c', CODE], cwd=ROOT,
                                    capture_output=True, text=True, timeout=12, env=environment,
                                    encoding='utf-8', errors='replace')
            outcome = dict(backend=backend, exit_code=result.returncode,
                           stdout=result.stdout, stderr=result.stderr, timed_out=False)
        except subprocess.TimeoutExpired as error:
            outcome = dict(backend=backend, exit_code=None, timed_out=True,
                           stdout=text(error.stdout), stderr=text(error.stderr))
        outcomes.append(outcome)
        print(outcome['stdout'], 'TIMEOUT' if outcome['timed_out'] else outcome['exit_code'])
    target = ROOT / 'artifacts' / 'audio-backend-probe.json'
    target.write_text(json.dumps(outcomes, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0 if all(not item['timed_out'] and item['exit_code'] == 0 for item in outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
