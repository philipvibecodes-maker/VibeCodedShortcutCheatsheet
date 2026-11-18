# Persistent topic column — revision 17

The running NotesWindow now keeps the same **Topic / Key / Value** columns for
empty searches, global searches, and empty results. Topic cells remain read-only.
An empty query still displays entries from the selected topic.

Actual X11 screenshots at 2× display scaling, using temporary sample data:

- [Empty search, full multiline values](full-multiline-values.png)
- [Empty search, inline value editing](inline-edit.png)
- [Empty search, collapsed sidebar at narrow width](narrow-collapsed.png)
- [Empty search, visible sidebar at narrow width](narrow-always-topics.png)
- [Global search, collapsed sidebar](collapsed-search.png)
- [Global search, visible sidebar](always-topics-search.png)
- [No matching results](empty-results.png)

Visual review confirmed the topic column is present without a query and values
still wrap into content-sized rows. The live harness verifies double-click/Enter
editing, Escape cancellation, full-value keyboard copying, and shortcut read-only
protection with the new fixed column positions.

Opening captures are also included: [Off](opening-0.mp4), [120ms](opening-120.mp4),
[180ms](opening-180.mp4). Animation settings are unchanged.

Reproduce with the current X11 display:

```sh
DISPLAY=:1 QT_QPA_PLATFORM=xcb venv/bin/python tools/review_notes_search.py /tmp/notes-review
QT_QPA_PLATFORM=offscreen venv/bin/python -m pytest tests/ -q
```

Full regression suite: **153 passed, 5 skipped**. A new regression checks column
labels, visibility, read-only topic cells and key/value contents while adding and
clearing queries, including queries with no matches.
