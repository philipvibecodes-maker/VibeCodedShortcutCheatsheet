# Palette polish — revision 10

[Before](before.mp4) · [After](after.mp4) · [Frame sequence](sequence.png) · [Settled](settled.png)

Both recordings use GNOME/X11, a 2× display, disposable demo notes, 180 ms,
startup speed 3, and 58% background blur opacity.

The revision 9 palette's heavy initial dimming made its text look disabled,
then progressively enabled while the panel moved and the backdrop blurred.
Revision 10 reduces the travel from 18 to 12 logical pixels and starts the
content reveal at 85%, instead of 35%. The remaining brightness change uses
a short quadratic ease-out, ending at 40% of eased motion progress. The cover
then disappears with identical pixels while the remaining movement settles.

Saved duration, startup speed, and backdrop opacity still apply. Fade and
full-screen slide behavior are unchanged. The native surface persists across
completion; the notes window stays excluded from backdrop blur.

Recorded with:

```sh
QT_QPA_PLATFORM=xcb venv/bin/python tools/record_notes_animation.py /tmp/palette-review --strategy palette --duration 180 --speed 3 --background blur
```

The frame sequence was decoded from the saved video after recording, rather
than capturing screenshots on the animation's event loop.
