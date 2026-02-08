"""Print the list of open application names every 500ms."""

import time

from src.platform.window_detection import get_open_app_names


while True:
    try:
        names = get_open_app_names()
        print(names)
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(0.5)
