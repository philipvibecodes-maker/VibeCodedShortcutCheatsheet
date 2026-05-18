"""Platform backend interface.

Defines the contract every platform backend (linux_gnome, windows, ...) must
satisfy. The dispatch layer in `src/platform/__init__.py` imports the concrete
implementation for the current OS and re-exports these names.
"""

from typing import Optional, Protocol, Tuple


class WindowDetection(Protocol):
    def is_platform_supported(self) -> Tuple[bool, str]:
        """Return (ok, human-readable message). Called once at startup."""
        ...

    def get_open_windows(self) -> list:
        """Return all visible top-level windows as a list of dicts."""
        ...

    def get_open_app_names(self) -> list:
        """Return the application name of every open window."""
        ...

    def get_focused_window(self) -> Optional[dict]:
        """Return the currently focused window dict, or None."""
        ...

    def get_focused_app_name(self) -> Optional[str]:
        """Return the focused application's name, or None."""
        ...


class WindowMovement(Protocol):
    def get_work_area(self) -> Optional[dict]:
        """Return {x, y, width, height} of the usable screen area, or None."""
        ...

    def get_corner_position(self, window, corner_v: str, corner_h: str):
        """Return (x, y) to position `window` in the given corner, or None."""
        ...
