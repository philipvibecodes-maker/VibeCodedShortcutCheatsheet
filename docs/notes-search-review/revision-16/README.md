# Full-value table review — revision 16

Screenshots of the actual running PyQt NotesWindow on X11 at 2× display scaling,
using disposable sample notes and shortcuts. The preview pane and compact summaries
are removed; the value column displays the complete multiline note directly.

## Visually inspected

- [Collapsed topics, active search](collapsed-search.png)
- [Always-visible topics, active search](always-topics-search.png)
- [Complete multiline values in the table](full-multiline-values.png)
- [Inline value editor](inline-edit.png)
- [Narrow window, topics visible](narrow-always-topics.png)
- [Narrow window, topics collapsed](narrow-collapsed.png)
- [Empty results](empty-results.png)

The value column occupies the space previously split with the preview. Rows expand
for line breaks and wrapping. Narrowing the table increases the sample note's row
height, keeping the full text readable without a second pane. Copy still preserves
complete stored values including trailing newlines.

## Live interaction checks

The native-app harness verifies double-click editing, Enter-to-edit for values,
Escape cancellation without changing stored content, the copy keyboard shortcut,
search-to-table focus, and read-only shortcut protection. Both sidebar layouts and
narrow-window screenshots are exercised. Only temporary demo storage is used.

Opening recordings: [Off](opening-0.mp4), [120ms](opening-120.mp4),
[180ms](opening-180.mp4). The [decoded frame sequence](opening-sequence.png) was
inspected after recording. The harness waits for recording readiness and types
immediately after showing notes. Existing animation and background preferences
remain unchanged.

## Reproduce and validation

```sh
DISPLAY=:1 QT_QPA_PLATFORM=xcb venv/bin/python tools/review_notes_search.py /tmp/notes-review
QT_QPA_PLATFORM=offscreen venv/bin/python -m pytest tests/ -q
```

Choose the current X11 display. The test suite passed: **152 passed, 5 skipped**.
Regression coverage includes full-value rendering beyond 100 characters, multiline
row heights after resizing/font changes, editing, copying, layout preferences,
readonly shortcuts, animation lifecycle, and backdrop behavior.
