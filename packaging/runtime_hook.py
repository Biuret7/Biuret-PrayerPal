"""Set application-specific defaults before Qt is imported by a windowed EXE."""
import os
import sys

if os.name == 'nt':
    os.environ.setdefault('QT_MEDIA_BACKEND', 'windows')
for name in ('stdout', 'stderr'):
    if getattr(sys, name) is None:
        setattr(sys, name, open(os.devnull, 'w', encoding='utf-8'))
