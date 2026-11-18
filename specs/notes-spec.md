## Notes window specs

The application has a notes window, separate from the cheatsheet window, that will
- open when the user presses the n key while the cheatsheet is focused, or toggle open/closed on the global Ctrl+Shift+\ hotkey (GNOME custom keybinding running `main.py --toggle-notes` on Linux, RegisterHotKey on Windows; both send a `toggle_notes` message over the local socket). Opening notes must not also show the cheatsheet (or the add-shortcuts settings window) — a `--toggle-notes` launch keeps the cheatsheet hidden.
- be large and centered on the screen.
- fade in the client content using a painted dark cover that fades away inside Qt (default 120 ms), while continuing to bypass GNOME's opening animation. Keep native window opacity at 100% throughout: the title bar and dark window surface appear immediately. Configure `notes_fade_in_duration_ms` in `data/config.json` (integer 0–1000; 0 disables the fade, invalid values use the default). Read the setting on each opening, stop the fade when hidden, and keep keyboard input available throughout.
- expose a keyboard-accessible Fade-in time slider in the Notes menu (0–1000 ms, showing Off at 0); save automatically on adjustment, preserving other settings, and apply the duration on the next opening.
- start the reveal immediately in the show event, without waiting for native exposure, using a cubic ease-out curve over the full configured duration. Begin with immediate visible progress and decelerate smoothly to the final state. Request updates every 8 ms using elapsed time, with no animation timer running after completion or hiding; do not queue an extra start timer. The cover spans the menu and content, follows resizing, passes input through, and is hidden after completion. Avoid native opacity changes, desktop captures, and widget graphics effects.
- reopen on the topic that was selected when it was last open (persisted to `config.json` as `notes_last_topic`, falling back to the first topic when it no longer exists).
- let the user record key/value pairs under user-defined topics (e.g. a topic `git` with a row "compare to origin main" and multi-line text as its value).
- show recorded app shortcuts as read-only topics named `shortcuts/<app_name>` (key = description, value = keys).
- have a search box that filters entries across all topics, showing the topic of each match. The last search text is persisted to `config.json` as `notes_last_search` and restored fully selected on reopen, so typing immediately replaces it.
- selecting a topic in the left menu clears the search and shows all entries in that topic.
- have buttons to add a topic, delete a topic, add an entry, edit an entry, and delete an entry (mnemonics + Ctrl+T / Ctrl+N / F2 / Delete).
- adjust font size with Ctrl+plus / Ctrl+minus, persisted to `config.json` as `notes_font_size`.
- close on Ctrl+Q and when the window loses focus (tabbing away).
- persist topics to `data/topics.json` immediately on every change.

- offer exclusive Fade reveal and Slide from top choices under Notes → Animation, persisted as `notes_animation_strategy` (default `fade`, alternative `slide`). Both use the duration slider; changes apply on the next opening. Slide moves the fully opaque window from above the available screen to its centered position with the same easing, and restores the final position when interrupted.
