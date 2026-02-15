## Specifications for the cheatsheet window
The cheatsheet window will
- start in the top right corner.
- be a standard window, not a borderless window.
- open when the application is launched.
- display the application name for the currently focused application (unless the currently focused application is this application, in which case the default shortcuts should be displayed.).
- show the shortcuts for the currently focused application, ( unless the currently focused application is this application, in which case, in which case the default shortcuts should be displayed.).
- display shortcuts in a table with 2 columns.
- display the shortcut's actions on the left column.
- display the shortcut's key combination in the right column.
- adjust the window size to fit the length and width of the table.
- be movable to the 4 corners of the screen with the arrow keys, sitting flush to the screen edges.
- control font size with ctrl + and ctrl -.
- have persistent font size between launches.
- use a dark theme.
- on non-wayland systems, expand to fill vertical space left by the retracted gnome bar when the focused application is 
in full screen mode.

## Full Screen Detection Implementation Details
To detect if the focused window is full screen, use the gnome extension api
to compare the height of the focused window to the height of the display. If they're 
identical, the focused window is in full screen, otherwise, it is not.
Note that the documentation for the Window Calls extension incorrectly states that the
List method returns the width and height of the windows. It does not.
Instead, use the List method to get the id of the focused window. Then use that
id to call the Details method, which does return the height and width of window with 
the provided id.
Also, make sure to skil polling when the focused window is from this app.

Make sure to
  - consider the display scaling when positioning the cheatsheet.
  - use standard Qt `move()` for window positioning (works under XWayland).
  - only use the application name to identify windows, not the window title or window pid.
  - not set a minimum height for the cheatsheet window.
  - not set a fixed width or height for the cheatsheet window.
  - use a grid layout of labels instead of QTableWidget, due to issues with how QTableWidget calculates its size.
  Relevant documentation:
  https://doc.qt.io/qtforpython-6/
  https://www.riverbankcomputing.com/static/Docs/PyQt6/
