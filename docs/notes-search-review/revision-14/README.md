# Notes search review — revision 14

These are screenshots of the running PyQt application on an X11 desktop at 2× display scaling,
using disposable sample notes and shortcuts. They are not mockups. Screenshots capture the live
Notes surface; recordings capture a sample desktop behind it. The harness never changes real
notes or preferences.

## Inspected scenarios

- [Collapsed topics with active search](collapsed-search.png)
- [Always-visible topics with the same active search](always-topics-search.png)
- [Complete multiline note preview](long-note-preview.png)
- [Explicit inline value editing](inline-edit.png)
- [Narrow window with topics](narrow-always-topics.png)
- [Narrow window with topics collapsed](narrow-collapsed.png)
- [Empty results](empty-results.png)

Both layouts retain readable selected-note content. At narrow widths, the preview moves below
results; the topic visibility choice remains independent of that responsive change. Inline editing
expands the value editor over adjacent rows without expanding every result. Management actions
stay in a compact menu, with explicit editing and copying visible.

## Opening comparison

[Off](opening-0.mp4) · [120ms](opening-120.mp4) · [180ms](opening-180.mp4)

[Opening frame sequence](opening-sequence.png)

All recordings use palette motion and 40% dim background; the existing background fade remains
independent. The harness types `compare` immediately after showing the window and asserts that
all characters reach search. Frames are decoded after recording to avoid disrupting animation. The recorder waits for its first
captured frame before opening notes. Keystrokes are spaced 10ms apart so Qt can paint between them.
The review also caught and fixed a hosted-window close/remap bug; a regression test verifies
that notes is truly hidden before the next opening. 180ms remains the default; existing saved settings remain authoritative.

## Reproduce

```sh
DISPLAY=:1 QT_QPA_PLATFORM=xcb venv/bin/python tools/review_notes_search.py /tmp/notes-search-review
```

Choose the current X11 display. The harness opens the actual NotesWindow with temporary storage,
records three openings, exercises both layouts and inline editing, and captures the live surface.
The output directory receives seven PNG screenshots and three MP4 recordings. Video dimensions
account for device pixel ratio. The frame sequence is an additional decoded review artifact.

Automated verification covers matching/order, selection, full-value copy, layout persistence,
readonly shortcuts, keyboard navigation, edit validation/cancellation/commit, focus-loss protection,
responsive sizing, saved appearance preferences, and reduced-motion behavior. Existing animation,
backdrop, and foreground-modal regression tests remain included.

Validation: `venv/bin/python -m pytest tests/ -q` — **151 passed, 5 skipped**.
