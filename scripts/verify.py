"""Run isolated, bounded validation and record exact commands and outcomes."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='Exercise native Windows Qt widgets')
    arguments = parser.parse_args()
    temporary = ROOT / '.test-tmp'
    temporary.mkdir(exist_ok=True)
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    platform = 'windows' if arguments.native else 'offscreen'
    environment = dict(os.environ, TEMP=str(temporary), TMP=str(temporary),
                       PYTHONIOENCODING='utf-8', QT_QPA_PLATFORM=platform)
    folders = ('biuret_prayerpal', 'tests', 'scripts')
    files = sorted(str(path.relative_to(ROOT)) for folder in folders
                   for path in (ROOT / folder).rglob('*.py')) + ['prayerpal.py']
    commands = [
        [sys.executable, 'prayerpal.py', '--self-test'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/gui', '-v'],
        [sys.executable, '-m', 'pycodestyle', '--max-line-length=99', *files],
        [sys.executable, '-m', 'compileall', '-q', 'biuret_prayerpal', 'tests', 'scripts',
         'prayerpal.py'],
        [sys.executable, 'scripts/smoke_preview.py', *(['--native'] if arguments.native else [])],
    ]
    outcomes = []
    for command in commands:
        print('Running:', ' '.join(command[:8]), flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, env=environment, text=True,
                                    encoding='utf-8', errors='replace', capture_output=True,
                                    timeout=45)
            outcome = dict(command=command, exit_code=result.returncode,
                           stdout=result.stdout, stderr=result.stderr)
        except subprocess.TimeoutExpired as error:
            outcome = dict(command=command, exit_code=None, timeout_seconds=45,
                           stdout=str(error.stdout or ''), stderr=str(error.stderr or ''))
        outcomes.append(outcome)
        outcome['skipped'] = 'skipped=' in outcome['stderr']
        outcome['successful'] = outcome['exit_code'] == 0 and not outcome['skipped']
        print('PASS' if outcome['successful'] else 'FAIL/INCOMPLETE', flush=True)
    report = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), platform=platform,
                  python=sys.version, outcomes=outcomes,
                  passed=all(item['successful'] for item in outcomes))
    target = output / f'verification-{platform}.json'
    if target.exists():
        history = output / 'history'
        history.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (history / f'verification-{platform}-{stamp}.json').write_bytes(target.read_bytes())
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Report: {target}')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
