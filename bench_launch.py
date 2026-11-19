"""Measure launch time of the cheatsheet window and notes window.

Usage: venv/bin/python bench_launch.py [--notes-reps N]
"""
import os
import sys
import time

if sys.platform.startswith("linux"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest


def fmt(ms):
    return f"{ms:8.1f} ms"


def main():
    notes_reps = 3
    if "--notes-reps" in sys.argv:
        notes_reps = int(sys.argv[sys.argv.index("--notes-reps") + 1])

    t0 = time.perf_counter()
    app = QApplication(sys.argv)
    t_app = time.perf_counter()

    t_imp0 = time.perf_counter()
    from src.cheatsheet.cheatsheet_window import CheatsheetWindow  # noqa: E402
    t_imp = time.perf_counter()

    t_ctor0 = time.perf_counter()
    window = CheatsheetWindow()
    t_ctor = time.perf_counter()

    t_show0 = time.perf_counter()
    window.show()
    QTest.qWaitForWindowExposed(window)
    t_exposed = time.perf_counter()

    print("=== Cheatsheet window launch ===")
    print(f"QApplication creation : {fmt((t_app - t0) * 1000)}")
    print(f"Module import         : {fmt((t_imp - t_imp0) * 1000)}")
    print(f"Window construction   : {fmt((t_ctor - t_ctor0) * 1000)}")
    print(f"show() -> exposed     : {fmt((t_exposed - t_show0) * 1000)}")
    print(f"TOTAL (process start -> exposed): {fmt((t_exposed - t0) * 1000)}")

    print("\n=== Notes window launch (toggle_notes, lazy create) ===")
    times = []
    for i in range(notes_reps):
        t_n0 = time.perf_counter()
        window.toggle_notes()
        QTest.qWaitForWindowExposed(window._notes_window)
        t_n1 = time.perf_counter()
        times.append((t_n1 - t_n0) * 1000)
        label = "cold (first)" if i == 0 else "warm"
        print(f"  rep {i + 1} [{label:>12}]: {fmt(times[-1])}")
        window._notes_window.close()
        app.processEvents()
        window._notes_window = None  # force re-create next rep
        time.sleep(0.5)  # stay clear of the 0.4s toggle debounce

    print(f"\nCold open: {fmt(times[0])}")
    if len(times) > 1:
        warm = times[1:]
        print(f"Warm avg : {fmt(sum(warm) / len(warm))}")

    sys.exit(0)


if __name__ == "__main__":
    main()
