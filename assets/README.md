# Read-only application assets

Everything in this directory is bundled at the same relative path under assets/.
Use biuret_prayerpal.resources.resource_path('assets/...') to read a bundled file.

sounds/chime.wav is the application's generated, non-speech chime. Place only
redistributable application assets here, not user settings, databases or secrets.
QSS and defaults currently live in Python modules and are collected as code.
