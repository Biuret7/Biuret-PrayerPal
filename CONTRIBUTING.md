# Contributing

Use a dedicated Python environment and keep the existing PySide6 binding. Keep core
calculations independent of Qt, preserve existing preferences, and avoid adding network
calls to the offline calculation path. Use a 99-character line limit.

```powershell
py -m pip install -r requirements-dev.txt
py prayerpal.py --self-test
py -m unittest discover -s tests/gui -v
py -m pycodestyle biuret_prayerpal tests scripts build.py prayerpal.py
```

Test audio with output muted. Run `python build.py` on Windows before proposing packaging
changes; keep the frozen smoke report. Never commit user registry exports, personal audio,
credentials, caches, build logs containing private paths, or generated executables to Git.
Release binaries belong under GitHub Releases. The included owner-supplied Adhan is an
explicit exception to the personal-audio exclusion; retain its attribution.
