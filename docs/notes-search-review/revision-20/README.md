# Dialog keyboard focus and mnemonics — revision 20

## Reproduction and fix

On the actual X11 desktop, saving New note returned Qt's active-window state to
Notes briefly, while `xdotool getwindowfocus` identified a different native window.
After 1.6 seconds Notes had also lost its Qt active-window state. A queued Qt
activation request alone reproduced the same failure.

The fix queues restoration after modal teardown, raises the actual Notes surface,
and explicitly restores native X11/XWayland input focus for Qt's xcb backend.
The table receives widget focus, or search when there are no entries. Focus-loss
dismissal is guarded during modal transitions. Hiding Notes cancels pending
restoration; there are no persistent focus retries.

The New note button now owns Alt+N through its mnemonic. The former Notes menu
is Settings (Alt+S), and the redundant explicit Alt+N shortcut is removed.

## Native verification

The live harness runs the real app with disposable data on X11 at 2× scaling:

- After Save, checks the X11 input-focus window ID against the actual Notes host.
- Waits beyond the focus-loss dismissal timeout and checks again.
- Sends real X11 `/` and typing events, verifies they reach Notes search.
- Opens New note with real Alt+N keystrokes and cancels the dialog.
- Checks native focus after Cancel and again beyond the dismissal timeout.

All five native focus comparisons matched: [focus-checks.json](focus-checks.json).
The [saved-note screenshot](new-note-saved.png) was inspected and shows Settings,
New note's mnemonic, the new entry, and search focused following the real typing check.

Additional live captures: [search prefill](new-note-search-prefill.png),
[selected-topic prefill](new-note-selected-topic.png),
[collapsed search](collapsed-search.png), [visible topics](always-topics-search.png),
[full values](full-multiline-values.png), [inline editing](inline-edit.png),
[narrow topics](narrow-always-topics.png), [narrow collapsed](narrow-collapsed.png),
[empty results](empty-results.png). Opening captures remain included:
[Off](opening-0.mp4), [120ms](opening-120.mp4), [180ms](opening-180.mp4).

## Reproduce

```sh
DISPLAY=:1 QT_QPA_PLATFORM=xcb venv/bin/python tools/review_notes_search.py /tmp/notes-review
QT_QPA_PLATFORM=offscreen venv/bin/python -m pytest tests/ -q
```

Choose the current X11 display; native input checks require xdotool. All app data
is temporary. Full suite: **171 passed, 5 skipped**, including Save/Cancel return
focus with fade/palette, hidden-window protection, and mnemonic conflict coverage.
