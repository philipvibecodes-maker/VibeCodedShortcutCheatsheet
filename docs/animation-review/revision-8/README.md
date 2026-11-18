# Notes animation review — revision 8

Captured on GNOME/X11 at 2560×1600 physical pixels, 2× scaling, 60 Hz.
The recordings use disposable demo notes and a synthetic desktop window, leaving
existing notes and settings untouched. Both comparison runs use a 360 ms slide,
startup speed 3, and 58% background opacity. Videos are encoded at 1280×800/60 fps.

- [Before](before.mp4)
- [After](after.mp4)
- [Frame sequence](sequence.png) — chronological, left to right, top to bottom
- [Settled screenshot](settled.png)
- [Before timing trace](before-timing.json) / [after timing trace](after-timing.json)

The old full-screen graphics-opacity effect performed poorly under recording
load: 7 opacity updates, with a median 52.1 ms between updates. Direct cached-image
painting produced 15 updates, median 19.3 ms, in the comparison run. These are
observed results under recording load, not guaranteed frame rates. Preparation
and display mapping are included in the trace's initial elapsed time. Frame
screenshots were extracted from recordings afterwards so taking screenshots did
not interrupt the animation event loop.

Changes:

- Paint cached blur directly, avoiding a full-screen intermediate opacity buffer.
- Pace updates to screen refresh (8–33 ms) rather than unconditionally 125 Hz.
- Skip native shape-mask updates when the notes geometry has not changed.
- Extend captured edge pixels before blur so screen edges do not become dark.
- Use 360 ms for slides with no saved duration; keep 120 ms for fades. Explicit
  durations, including 0, and startup-speed choices are preserved.
- Retain the same native surface at completion and keep the notes exclusion mask.

Reproduce from a GNOME/X11 desktop session with ffmpeg installed:

```sh
QT_QPA_PLATFORM=xcb venv/bin/python tools/record_notes_animation.py /tmp/notes-review --duration 360 --speed 3
```

The script shows a temporary full-screen sample background, opens notes once,
records the screen, and closes its own windows. `DISPLAY` and `XAUTHORITY` must
refer to the desktop being recorded. It records that desktop, including any
system notifications shown over the demo. The automated offscreen tests verify
blur edge color, opacity, scaling, mask exclusion, and window lifecycle; they
cannot establish compositor smoothness.
