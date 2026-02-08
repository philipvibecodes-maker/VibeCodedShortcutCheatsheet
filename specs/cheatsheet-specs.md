## Specifications for the cheatsheet window
The cheatsheet window will
- be a standard window, not a borderless window.
- open when the application is launched.
- display the application name for the currently focused application (unless the currently focused application is this application).
- show the shortcuts for the currently focused application, (unless the currently focused application is this application).
- display shortcuts in a table with 2 columns.
- display the shortcut's actions on the left column.
- display the shortcut's key combination in the right column.
- adjust it's size to fit the length and width of the table
- be movable to the 4 corners of the screen with the arrow keys.
- control font size with ctrl + and ctrl -.
- have persistent font size between launches.
- use a dark theme

Make sure to
  - considering the resolution of the display when positioning the cheatsheet 
  - use the dbus api for the "windows-calls" gnome extension, because the standard move function
  in PyQt does not function on Wayland systems.
  - only use the application name to identify windows, not the window title or window pid.
  - not set a minimum height for the cheatsheet window.
  - not set a fixed width or height for the cheatsheet window.

  Relevant documentation:
  https://doc.qt.io/qtforpython-6/
  https://www.riverbankcomputing.com/static/Docs/PyQt6/
