# Phase 3 shell captures

22 viewport screenshots from the actual shell, captured on 11 October 2026.
Environment: macOS 27.0.1 ARM64, Python 3.12.7, Playwright 1.63.0,
Chromium 153.0.8010.12. See [Phase 3 notes](../../PHASE_3_SHELL.md) and
[the machine-readable check report](../../shell-checks.json).

| View | Light | Dark |
|---|---|---|
| Welcome 360×800 | [PNG](light-360-welcome.png) | [PNG](dark-360-welcome.png) |
| Welcome 768×900 | [PNG](light-768-welcome.png) | [PNG](dark-768-welcome.png) |
| Welcome 1024×900 | [PNG](light-1024-welcome.png) | [PNG](dark-1024-welcome.png) |
| Welcome 1440×1000 | [PNG](light-1440-welcome.png) | [PNG](dark-1440-welcome.png) |
| Collapsed sidebar 1440 | [PNG](light-1440-collapsed.png) | [PNG](dark-1440-collapsed.png) |
| Navigation drawer 360 | [PNG](light-360-navigation.png) | [PNG](dark-360-navigation.png) |
| Navigation drawer 768 | [PNG](light-768-navigation.png) | [PNG](dark-768-navigation.png) |
| Appearance dialog 360 | [PNG](light-360-settings.png) | [PNG](dark-360-settings.png) |
| Appearance dialog 1440 | [PNG](light-1440-settings.png) | [PNG](dark-1440-settings.png) |
| Documents entry point 1440 | [PNG](light-1440-documents.png) | [PNG](dark-1440-documents.png) |
| Offline draft 1440 | [PNG](light-1440-offline.png) | [PNG](dark-1440-offline.png) |

Health values in these captures are **explicit browser-test fixtures**; the
offline screenshots use browser-context offline mode. A separately recorded
real health smoke checks the existing FastAPI server. These screenshots show
shell and draft behavior, not generated chat answers or uploaded documents.

The composer stays docked while the welcome region scrolls on shorter screens.
The runner also selects all six prompts, verifies their accessibility and
draft focus, and checks 768×450 landscape geometry. The narrower welcome
screenshots intentionally show the first viewport rather than a stitched image.

Regenerate with `python scripts/verify_shell.py --capture`. Adding
`--live http://localhost:8000` also records the real health smoke.
