# V1.0.1 — 2026-10-21

- Popup duration has explicit −/+ buttons, a 4–30 second hint, and mouse/typing/preview/save regression coverage.
- Mouse clicks no longer retain a bright focus border; keyboard focus stays visible.
- Clear current-prayer label and explicit "Sunrise today" information.
- Informative idle audio state; Stop Audio appears while playback is active.
- Animated sun/moon button and theme crossfade; respects reduced motion and rapid toggles.
- Arabic/English interface including settings, tray menu and reminder text; stable stored IDs.
- Opt-in current-user Windows login startup, with registry rollback on preference failure.
- Rounded settings panes across all six tabs and clean numeric/time input borders.
- Versioned local build outputs and additional source/frozen verification.

Windows x64 installer, bundled Adhan and source are available in the V1.0.1 release.
The app and installer are unsigned; clean-PC and real login-session checks remain unverified.

# V1.0.0 — 2026-10-20

Installer packaging update: the primary EXE download now runs a per-user setup wizard.
Includes Arabic/English pages, shortcuts, Windows uninstall registration, guarded
reinstallation and preserved user preferences. Application payload remains unchanged.

First public GitHub release. Internal 4.x prototypes preceded this public version.

- Offline prayer calculations, next-prayer countdown, and customizable reminders.
- Dark/light RTL interface, five popup positions, fade/slide/zoom, and unsaved previews.
- Bundled Adhan by Omar Hisham Al Arabi, selectable without browsing for a file.
- Local preferences, audio ownership guards, volume/mute, and Stop Audio.
- Portable Windows x64 GUI EXE with icon, timezone data, media plugins and bundled sounds.
- Safe build staging, executable validation, and muted frozen WAV/MP3 smoke checks.
- Arabic/English README, build guide, recording attribution, and regression tests.

The EXE is unsigned. Clean-PC certification, signing, manual accessibility and
multi-monitor/hardware coverage remain unverified.
