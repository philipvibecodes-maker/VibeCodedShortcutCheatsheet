"""Print the focused application name every 500ms for 5 seconds."""

import time

from src.platform.window_detection import get_focused_app_name


start = time.time()
while time.time() - start < 5:
    try:
        app_name = get_focused_app_name()
        print(app_name)
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(0.5)
