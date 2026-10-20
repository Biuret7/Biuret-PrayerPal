"""Single-owner Qt audio playback and atomic, locally synthesized chimes."""
from __future__ import annotations

import math
import os
import struct
import tempfile
import wave
from pathlib import Path
from .resources import resource_path

# This audio-only Windows application uses the supported native Qt 6 backend.
# The installed Qt 6.12 FFmpeg backend stalled during hardware-codec discovery
# even for a PCM WAV. Honor an explicit deployment override for other backends.
# See docs/UPGRADE_REPORT.md for the probe and Qt deprecation tradeoff.
if os.name == 'nt':
    os.environ.setdefault('QT_MEDIA_BACKEND', 'windows')


def _valid_chime(path: Path) -> bool:
    try:
        with wave.open(str(path), 'rb') as source:
            return (source.getnchannels() == 1 and source.getsampwidth() == 2
                    and source.getframerate() == 22050 and source.getnframes() > 10000
                    and len(source.readframes(source.getnframes())) == source.getnframes() * 2)
    except (OSError, EOFError, wave.Error):
        return False


def write_chime(path: Path) -> Path:
    """Publish a complete WAV using same-directory atomic replacement.

    An interrupted write cannot turn the next startup's chime into a partial WAV.
    Existing files are inspected, not trusted just because they are large enough.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if _valid_chime(path):
        return path
    rate = 22050
    frames = bytearray()
    for frequency, duration in ((523.25, 0.28), (659.25, 0.30)):
        count = int(rate * duration)
        for n in range(count):
            t = n / rate
            envelope = math.sin(math.pi * n / count) ** 1.7
            tone = (math.sin(2 * math.pi * frequency * t)
                    + 0.25 * math.sin(4 * math.pi * frequency * t))
            frames.extend(struct.pack('<h', max(-32767, min(32767, int(tone * envelope * 8000)))))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.wav', delete=False) as stream:
            temporary = Path(stream.name)
            with wave.open(stream, 'wb') as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(rate)
                output.writeframes(frames)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


try:
    from PySide6.QtCore import QObject, QStandardPaths, QThread, QUrl, Signal
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:
    # Pure WAV helper remains usable by the Qt-independent test suite.
    pass
else:
    class SoundService(QObject):
        """Latest request owns audio; stale errors/dismissals cannot stop its successor.

        All public operations run on the service's Qt thread. QMediaPlayer handles
        decoding asynchronously; no Python worker locks, waits, or thread joins.
        """
        error_message = Signal(str)
        active_changed = Signal(bool)

        def __init__(self, parent=None, chime_path=None):
            super().__init__(parent)
            self.output = QAudioOutput(self)
            self.player = None
            self._generation = 0
            self._active = False
            self._bundled_chime = resource_path(
                'assets/sounds/chime.wav') if chime_path is None else None
            self.chime_path = Path(chime_path) if chime_path else Path(
                QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            ) / 'chime.wav'

        def _check_thread(self):
            if QThread.currentThread() != self.thread():
                raise RuntimeError('SoundService must be used on its owning Qt thread.')

        def _retire_player(self):
            self._set_active(False)
            if self.player is not None:
                player, self.player = self.player, None
                player.stop()
                player.setAudioOutput(None)
                player.deleteLater()

        def _set_active(self, active):
            if self._active != active:
                self._active = active
                self.active_changed.emit(active)

        def _on_state(self, generation, state):
            if generation == self._generation:
                self._set_active(state == QMediaPlayer.PlaybackState.PlayingState)

        def _on_error(self, generation, error, _detail):
            if generation == self._generation and error != QMediaPlayer.Error.NoError:
                self._set_active(False)
                self.error_message.emit('تعذّر تشغيل الصوت. تحقق من الملف وصيغته وجهاز الإخراج.')

        def play(self, prefs, kind: str) -> int:
            self._check_thread()
            prefs.validate()
            self._generation += 1
            generation = self._generation
            self._retire_player()
            if prefs.muted or prefs.volume == 0 or prefs.sound_mode == 'none':
                return generation
            try:
                if prefs.sound_mode == 'chime':
                    source = (self._bundled_chime if self._bundled_chime is not None
                              and self._bundled_chime.is_file() else write_chime(self.chime_path))
                elif prefs.sound_mode == 'bundled_adhan':
                    source = resource_path('assets/sounds/adhan-omar-hisham-al-arabi.mp3')
                else:
                    selected = (prefs.adhan_file if prefs.sound_mode == 'adhan'
                                else prefs.azkar_file)
                    if not selected:
                        raise FileNotFoundError('No audio selected')
                    source = Path(selected).expanduser().resolve(strict=True)
                    if not source.is_file():
                        raise FileNotFoundError('Not an audio file')
                # Verify readability before asking the asynchronous backend to load.
                with source.open('rb') as stream:
                    if not stream.read(1):
                        raise OSError('Empty audio file')
            except (OSError, ValueError, wave.Error):
                self.error_message.emit('ملف الصوت غير متاح. اختر ملفاً صالحاً من الإعدادات.')
                return generation
            self.output.setVolume(prefs.volume / 100.0)
            self.player = QMediaPlayer(self)
            self.player.setAudioOutput(self.output)
            self.player.errorOccurred.connect(
                lambda error, detail, token=generation: self._on_error(token, error, detail))
            self.player.playbackStateChanged.connect(
                lambda state, token=generation: self._on_state(token, state))
            self.player.setSource(QUrl.fromLocalFile(str(source)))
            self.player.play()
            return generation

        def stop(self, token=None) -> None:
            self._check_thread()
            if token is not None and token != self._generation:
                return
            self._generation += 1
            self._retire_player()
