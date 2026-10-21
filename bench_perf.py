"""Performance benchmark for the Shortcut Cheatsheet app.

Measures, at a configurable focus-poll frequency (default 10 Hz, matching the
100 ms timer in CheatsheetWindow):

  * Launch latency: QApplication -> import -> construct -> exposed, plus a
    real subprocess launch of main.py until the cheatsheet window is mapped.
  * Cheatsheet open/close latency over repeated cycles.
  * Notes window open/close latency (cold and warm) via toggle_notes().
  * Focus-switch latency: unprofiled app -> profiled app and back.
  * Memory (VmRSS / VmHWM) at each stage.
  * Steady-state CPU utilization of the polling loop.

Usage:
    venv/bin/python bench_perf.py [--poll-hz N] [--reps N] [--cpu-secs S]
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time

if sys.platform.startswith("linux"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP_WITH_RECORDS = "bench-target"
APP_NO_RECORDS = "bench-empty-app"
NUM_BENCH_SHORTCUTS = 15
SERVER_NAME = "ShortcutCheatsheet"


# --- /proc helpers ---------------------------------------------------------

def rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    return 0.0


def hwm_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) / 1024.0
    return 0.0


def cpu_jiffies():
    with open("/proc/self/stat") as f:
        parts = f.read().rsplit(")", 1)[1].split()
    # fields 13/14 (utime/stime) are indices 11/12 after the comm split
    return int(parts[11]) + int(parts[12])


CLK_TCK = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


def cpu_percent_since(jiffies0, t0):
    d_jiffies = cpu_jiffies() - jiffies0
    d_secs = time.perf_counter() - t0
    return 100.0 * (d_jiffies / CLK_TCK) / d_secs if d_secs > 0 else 0.0


# --- timing helpers --------------------------------------------------------

def fmt(ms):
    return f"{ms:7.1f} ms"


def summarize(label, samples):
    if not samples:
        return
    line = (
        f"  {label:<38} mean {statistics.mean(samples):7.1f} ms  "
        f"median {statistics.median(samples):7.1f} ms  "
        f"min {min(samples):7.1f}  max {max(samples):7.1f}  n={len(samples)}"
    )
    print(line)


# --- benchmark data --------------------------------------------------------

def ensure_bench_profile():
    path = os.path.join("data", f"{APP_WITH_RECORDS}.json")
    data = {
        "app_name": APP_WITH_RECORDS,
        "display_name": "Benchmark Target",
        "shortcuts": [
            {"keys": f"Ctrl+Alt+{i}", "description": f"Benchmark shortcut number {i}"}
            for i in range(NUM_BENCH_SHORTCUTS)
        ],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def remove_bench_profile():
    path = os.path.join("data", f"{APP_WITH_RECORDS}.json")
    if os.path.exists(path):
        os.unlink(path)


# --- subprocess launch latency --------------------------------------------

def measure_subprocess_launch(reps):
    """Spawn real `main.py`; time until the QLocalServer accepts connections
    (server.listen happens immediately before window.show())."""
    from PyQt6.QtNetwork import QLocalSocket

    samples = []
    for _ in range(reps):
        t0 = time.perf_counter()
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = t0 + 20
        connected = False
        while time.perf_counter() < deadline:
            sock = QLocalSocket()
            sock.connectToServer(SERVER_NAME)
            if sock.waitForConnected(50):
                connected = True
                sock.disconnectFromServer()
                break
            time.sleep(0.005)
        t1 = time.perf_counter()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        # ensure the socket name is free for the next rep
        from PyQt6.QtNetwork import QLocalServer
        QLocalServer.removeServer(SERVER_NAME)
        if connected:
            samples.append((t1 - t0) * 1000)
        time.sleep(0.3)
    return samples


# --- phases ----------------------------------------------------------------

def phase_launch(app, reps):
    print("\n=== Phase 1: launch latency ===")
    t0 = time.perf_counter()
    from src.cheatsheet.cheatsheet_window import CheatsheetWindow
    t_imp = time.perf_counter()
    window = CheatsheetWindow(open_settings_for_new_app=False)
    t_ctor = time.perf_counter()
    window.show()
    QTest.qWaitForWindowExposed(window)
    t_exp = time.perf_counter()
    print(f"  module import                        : {fmt((t_imp - t0) * 1000)}")
    print(f"  CheatsheetWindow() construction      : {fmt((t_ctor - t_imp) * 1000)}")
    print(f"  show() -> exposed                    : {fmt((t_exp - t_ctor) * 1000)}")
    print(f"  RSS after show                       : {rss_mb():7.1f} MB (peak {hwm_mb():.1f} MB)")
    sub = measure_subprocess_launch(reps)
    summarize("subprocess main.py -> IPC ready", sub)
    return window


def phase_cheatsheet_open_close(app, window, reps):
    print("\n=== Phase 2: cheatsheet open/close ===")
    open_ms, close_ms = [], []
    j0, t0 = cpu_jiffies(), time.perf_counter()
    for _ in range(reps):
        t_o = time.perf_counter()
        window.show()
        QTest.qWaitForWindowExposed(window)
        open_ms.append((time.perf_counter() - t_o) * 1000)
        t_c = time.perf_counter()
        window.hide()
        app.processEvents()
        close_ms.append((time.perf_counter() - t_c) * 1000)
    summarize("open  (show -> exposed)", open_ms)
    summarize("close (hide -> processed)", close_ms)
    print(f"  CPU during loop                      : {cpu_percent_since(j0, t0):5.1f} %")
    print(f"  RSS                                  : {rss_mb():7.1f} MB (peak {hwm_mb():.1f} MB)")


def phase_notes_open_close(app, window, reps):
    print("\n=== Phase 3: notes window open/close ===")
    open_ms, close_ms = [], []
    j0, t0 = cpu_jiffies(), time.perf_counter()
    for i in range(reps):
        window._last_notes_toggle = 0  # bypass the 0.4 s debounce for benchmarking
        t_o = time.perf_counter()
        window.toggle_notes()
        QTest.qWaitForWindowExposed(window._notes_window)
        open_ms.append((time.perf_counter() - t_o) * 1000)
        window._last_notes_toggle = 0
        t_c = time.perf_counter()
        window.toggle_notes()  # closes it
        app.processEvents()
        close_ms.append((time.perf_counter() - t_c) * 1000)
        label = "cold" if i == 0 else "warm"
        print(f"    rep {i + 1} [{label}]: open {fmt(open_ms[-1])}  close {fmt(close_ms[-1])}")
    summarize("open  (toggle -> exposed)", open_ms)
    summarize("close (toggle -> hidden)", close_ms)
    print(f"  CPU during loop                      : {cpu_percent_since(j0, t0):5.1f} %")
    print(f"  RSS                                  : {rss_mb():7.1f} MB (peak {hwm_mb():.1f} MB)")


def phase_focus_switch(app, window, platform_mod, reps):
    print("\n=== Phase 4: focus switch, no-profile app -> profiled app ===")
    import src.cheatsheet.cheatsheet_window as cw

    real_get_focused = cw.get_focused_window
    state = {"app": APP_NO_RECORDS, "title": "Empty Window"}
    cw.get_focused_window = lambda: {
        "wm_class": state["app"],
        "title": state["title"],
        "focus": True,
    }

    # seed state: focused on the empty app
    window._current_app = APP_NO_RECORDS
    window._current_title = state["title"]
    window.hide()
    app.processEvents()

    poll_ms, show_ms, hide_ms = [], [], []
    for _ in range(reps):
        # switch to profiled app
        state["app"], state["title"] = APP_WITH_RECORDS, "Bench Window"
        t_p = time.perf_counter()
        window._on_poll()
        poll_ms.append((time.perf_counter() - t_p) * 1000)
        t_s = time.perf_counter()
        QTest.qWaitForWindowExposed(window)
        show_ms.append((time.perf_counter() - t_p) * 1000)
        _ = t_s

        # switch back to unprofiled app
        state["app"], state["title"] = APP_NO_RECORDS, "Empty Window"
        t_h = time.perf_counter()
        window._on_poll()
        app.processEvents()
        hide_ms.append((time.perf_counter() - t_h) * 1000)

    summarize("_on_poll call (resolve+display)", poll_ms)
    summarize("switch to profiled -> exposed", show_ms)
    summarize("switch to empty -> hidden", hide_ms)
    print(f"  RSS                                  : {rss_mb():7.1f} MB (peak {hwm_mb():.1f} MB)")
    cw.get_focused_window = real_get_focused


def phase_poll_cpu(app, window, platform_mod, hz, secs):
    print(f"\n=== Phase 5: steady-state CPU of polling loop @ {hz} Hz ===")
    interval_ms = max(1, round(1000 / hz))
    window._poll_timer.setInterval(interval_ms)
    calls = {"n": 0, "total": 0.0}
    orig = window._on_poll

    def timed():
        t = time.perf_counter()
        orig()
        calls["n"] += 1
        calls["total"] += time.perf_counter() - t

    window._poll_timer.timeout.disconnect()
    window._poll_timer.timeout.connect(timed)

    # constant focus -> the cheap early-return path of _on_poll
    j0, t0 = cpu_jiffies(), time.perf_counter()
    end = t0 + secs
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.0005)
    elapsed = time.perf_counter() - t0

    n, total = calls["n"], calls["total"]
    print(f"  timer interval set to {interval_ms} ms")
    print(f"  polls executed        : {n} in {elapsed:.1f} s "
          f"({n / elapsed:.0f} polls/s actual)")
    if n:
        print(f"  avg _on_poll cost     : {total / n * 1000:.3f} ms")
    print(f"  CPU utilization       : {cpu_percent_since(j0, t0):5.1f} %")
    print(f"  RSS                   : {rss_mb():7.1f} MB (peak {hwm_mb():.1f} MB)")

    window._poll_timer.timeout.disconnect()
    window._poll_timer.timeout.connect(orig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--poll-hz", type=float, default=10.0)
    parser.add_argument("--reps", type=int, default=15)
    parser.add_argument("--cpu-secs", type=float, default=4.0)
    args = parser.parse_args()

    ensure_bench_profile()
    try:
        app = QApplication(sys.argv)
        import src.platform as platform_mod
        window = phase_launch(app, max(2, args.reps // 3))

        interval_ms = max(1, round(1000 / args.poll_hz))
        window._poll_timer.setInterval(interval_ms)

        phase_cheatsheet_open_close(app, window, args.reps)
        phase_notes_open_close(app, window, args.reps)
        phase_focus_switch(app, window, platform_mod, args.reps)
        phase_poll_cpu(app, window, platform_mod, args.poll_hz, args.cpu_secs)
    finally:
        remove_bench_profile()

    print("\nDone.")


if __name__ == "__main__":
    main()
