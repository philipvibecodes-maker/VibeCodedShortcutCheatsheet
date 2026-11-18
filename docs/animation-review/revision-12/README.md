# Distinguishing focus change from background fade — revision 12

[Before](before.mp4) · [After: dark scrim](dim.mp4) · [After: refreshed blur](blur.mp4)

[Frame sequence](sequence.png) · [Settled background](settled.png) · [Blur screenshot](blur.png) · [Controls](controls.png)

The previous background followed the window's fast ease-out curve. On a 180 ms
palette opening, much of the darkening coincided with the other window losing
focus. Blur also captured the old active title-bar colors before that change.

Revision 12 gives backgrounds their own linear 320 ms fade, queued 75 ms after
opening. Window motion still starts immediately. The short focus-settling period
makes the native focus transition and subsequent full-desktop darkening separate
observable events. The background can keep fading after the window lands; landing
does not snap the scrim to its target strength.

The **Background fade time** slider saves independently (0–1000 ms, default 320).
It applies on the next opening. Setting window animation duration to zero no
longer disables the independent background fade; set background fade time to zero
as well to show it immediately after focus settling. Opacity remains adjustable
live, and style/animation preferences are preserved.

For blur, a second desktop capture after focus settling supplies the new inactive
chrome colors. Notes and a shadow margin are replaced from the clean pre-opening
capture before blur, preventing foreground notes from being baked into their own
background. Both captures remain in memory; the clean original is discarded once
the refreshed blur is ready. Dark and spotlight styles still need no capture.

## Visual verification

Recorded on GNOME/X11 at 2× scaling with disposable demo content, a 180 ms palette
entrance, startup speed 3, and 58% background opacity. The sample background has
a title-color indicator driven by real Qt activation events; it makes the active
to inactive transition easy to identify without relying on the OS title-bar theme.
It is a test indicator, not a modification to another application's title bar.

The [timing trace](dim-timing.json) records 19 independent background opacity
updates, from about 163 to 468 ms after `show()` was called. This includes opening
preparation in the initial timestamp; the difference between first and last fade
updates is about 305 ms. Results are observational under recording load, not a
frame-rate guarantee. The first recorded fade update occurs after time zero;
the configured total remains 320 ms. Screenshots were decoded from the completed
video so capture did not interrupt the animation timer. Exported clips crop a
narrow right edge to exclude unrelated desktop content.

Tests verify independence from motion, cancellation on hide/close, disabled fades,
configuration persistence, and post-focus blur refresh without foreground capture,
including high-DPI coordinates. The original mask and rendering tests still pass.

```sh
QT_QPA_PLATFORM=xcb venv/bin/python tools/record_notes_animation.py /tmp/focus-review --strategy palette --duration 180 --background dim --focus-chrome
```

Use `--background blur` to check refreshed chrome, or `--menu` to inspect the new
background fade control. The tool records a temporary sample background and
keeps notes/configuration in a temporary directory.
