# New note topic prefill — revision 19

The footer now includes New note alongside New topic. The modal form has an
editable Topic selector, Key, and multiline Value. These captures are from the
running PyQt app on X11 at 2× display scaling, using temporary sample data.

## Inspected new-note flow

- [Search prefill](new-note-search-prefill.png): search is `review`; the last
  result is selected, but Topic is `Git commands`, from the first result.
- [Saved note](new-note-saved.png): change the destination to `Daily notes`,
  enter a key/value, and save with Ctrl+Enter. Search clears and the new note is
  selected under its destination topic.
- [Selected-topic prefill](new-note-selected-topic.png): with search empty,
  Topic is `Daily notes`. Cancelling creates no note and changes no data.

The live harness clicks the visible New note button and interacts with real
modal dialogs. It asserts topic prefill, successful persistence, current topic,
search clearing, selected note, and cancellation behavior. Other live interaction
checks cover inline editing, cancellation, full-value copying and read-only
shortcuts. Key and Value labels have working keyboard mnemonics.

## Additional captures

[Collapsed search](collapsed-search.png), [visible topics](always-topics-search.png),
[full values](full-multiline-values.png), [inline editing](inline-edit.png),
[narrow visible topics](narrow-always-topics.png),
[narrow collapsed topics](narrow-collapsed.png), [empty results](empty-results.png).

Opening captures: [Off](opening-0.mp4), [120ms](opening-120.mp4),
[180ms](opening-180.mp4). Opening behavior is unchanged.

## Validation and reproduction

```sh
DISPLAY=:1 QT_QPA_PLATFORM=xcb venv/bin/python tools/review_notes_search.py /tmp/notes-review
QT_QPA_PLATFORM=offscreen venv/bin/python -m pytest tests/ -q
```

Choose the current X11 display. The full suite passed: **165 passed, 5 skipped**.
Regression coverage includes search-first prefill independent of selected result,
current-topic prefill, whitespace/no-match fallback, an empty library, new-topic
creation on save, cancellation, and rejection of blank/read-only destinations.
