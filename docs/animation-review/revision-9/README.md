# Command palette animation — revision 9

- [GNOME recording](command-palette.mp4)
- [Frame sequence](sequence.png), chronological left-to-right then top-to-bottom
- [Settled screenshot](settled.png)

Recorded on GNOME/X11, 2× scaling, using disposable demo notes and a synthetic
desktop. Configuration: palette strategy, 180 ms, startup speed 3, backdrop 58%.

The palette moves down 18 logical pixels while its content reveals, avoiding the
long offscreen slide. The same native surface and title bar remain after opening.
Reviewing initial footage exposed an opaque cover under GNOME; direct transparent
painting fixes the blank rectangle before the content appears. The final recording
above was captured after that fix and inspected frame by frame.

Reproduce from the desktop session:

```sh
QT_QPA_PLATFORM=xcb venv/bin/python tools/record_notes_animation.py /tmp/palette-review --strategy palette --duration 180 --speed 3
```
