# Foreground notes dialogs — revision 13

[Alt+T recording](alt-t.mp4) · [New topic screenshot](new-topic.png)

Recorded on GNOME/X11 with disposable demo notes and a synthetic desktop.
The harness sends Alt+T to notes, waits with the modal dialog visible, then
cancels it and closes the demo. The screenshot confirms New topic is centered
above notes with the input caret visible. The exported clip crops desktop edges
to keep unrelated content outside the demonstration.

The previous native dialog was managed by GNOME while the animated notes host
bypassed the window manager. The shared dialog path now gives modal notes dialogs
topmost/override-redirect stacking too. It handles New topic, New entry, and
Delete topic confirmation, centering after mapping and restoring focus on return.

Automated regression tests invoke Alt+T with fade, slide, and palette strategies,
verify modality/stacking flags/input focus/centering, enter a topic, and confirm
persistence. Cancel, entry creation, and confirmation cancellation are also tested.

```sh
QT_QPA_PLATFORM=xcb venv/bin/python tools/record_notes_animation.py /tmp/topic-review --strategy palette --duration 180 --background dim --topic-dialog
```
