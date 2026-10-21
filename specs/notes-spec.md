## Notes window specs

The application has a notes window, separate from the cheatsheet window, that will
- open when the user presses the n key while the cheatsheet is focused, or toggle open/closed on the global Ctrl+Shift+\ hotkey (GNOME custom keybinding running `main.py --toggle-notes` on Linux, RegisterHotKey on Windows; both send a `toggle_notes` message over the local socket). Opening notes must not also show the cheatsheet (or the add-shortcuts settings window) — a `--toggle-notes` launch keeps the cheatsheet hidden.
- be large and centered on the screen.
- reopen on the topic that was selected when it was last open (persisted to `config.json` as `notes_last_topic`, falling back to the first topic when it no longer exists).
- let the user record key/value pairs under user-defined topics (e.g. a topic `git` with a row "compare to origin main" and multi-line text as its value).
- show recorded app shortcuts as read-only topics named `shortcuts/<app_name>` (key = description, value = keys).
- have a search box that filters entries across all topics, showing the topic of each match. The last search text is persisted to `config.json` as `notes_last_search` and restored fully selected on reopen, so typing immediately replaces it.
- have buttons to add a topic, delete a topic, add an entry, edit an entry, and delete an entry (mnemonics + Ctrl+T / Ctrl+N / F2 / Delete).
- adjust font size with Ctrl+plus / Ctrl+minus, persisted to `config.json` as `notes_font_size`.
- close on Ctrl+Q and when the window loses focus (tabbing away).
- persist topics to `data/topics.json` immediately on every change.
