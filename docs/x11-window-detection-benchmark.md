# X11 window detection benchmark

Date: 2026-10-21

## Question

Can the `window-calls` GNOME extension requirement be waived on X11, and would
removing it improve window-detection performance?

## Test environment

- Ubuntu/GNOME desktop session
- `XDG_SESSION_TYPE=x11`
- `DISPLAY=:0`
- 4 windows in `_NET_CLIENT_LIST`
- Existing `gdbus` implementation compared with X11 prototypes using `xprop`
  and direct `libX11` calls through `ctypes`

## Findings

A real X11 session exposes all required window metadata through standard EWMH
properties:

- `_NET_ACTIVE_WINDOW`: focused window ID
- `_NET_CLIENT_LIST`: top-level client window IDs
- `WM_CLASS`: application instance and class
- `_NET_WM_NAME` / `WM_NAME`: window title
- `_NET_WM_PID`: process ID

The values returned by these properties matched the current `window-calls`
output, including `wm_class` values such as `Gnome-terminal`,
`Brave-browser`, and `org.signal.Signal`.

## Measured results

| Operation / implementation | Mean | Median | Notes |
|---|---:|---:|---|
| `get_focused_window()` via `gdbus` | ~3.0 ms | ~2.96 ms | Current implementation |
| Focused window via `xprop` | ~2.19 ms | ~2.15 ms | Two subprocesses |
| Focused window via `libX11`/`ctypes` | ~0.059 ms | ~0.058 ms | No subprocess |
| `get_open_windows()` via `gdbus` | ~3.02 ms | ~2.90 ms | Current implementation |
| Window list via `xprop` | ~6.33 ms | ~6.24 ms | One subprocess per window; slower |
| Window list via `libX11`/`ctypes` | ~0.209 ms | ~0.203 ms | No subprocess |

The focused-window path is the hot path because the cheatsheet polls it every
100 ms. At that rate, the current implementation spends roughly 30 ms/sec of
wall-clock time querying focused-window state. A direct `libX11` implementation
would spend roughly 0.6 ms/sec, about a 50x speedup and a ~98% reduction.

A subprocess-based `xprop` backend would improve focused lookup only modestly
and would regress full window enumeration because it requires one subprocess
per client window.

## Recommendation

Waive the `window-calls` requirement on X11, but implement X11 detection with
`libX11` through `ctypes` rather than by shelling out to `xprop`.

Keep `window-calls` for Wayland. Do not decide based on `DISPLAY` alone: under
Wayland the app forces `QT_QPA_PLATFORM=xcb`, so `DISPLAY` can exist through
XWayland while native Wayland windows remain invisible to X11 property queries.
Dispatch on `XDG_SESSION_TYPE=x11` instead.

## Implemented

`src/platform/linux_gnome/x11_window_detection.py` now implements all five
detection functions via `libX11`/`ctypes`; `src/platform/__init__.py` selects it
when `XDG_SESSION_TYPE=x11` and falls back to `window-calls` otherwise.

Post-change measurements (in-app `bench_perf.py`, real `get_focused_window`
polling):

| Poll rate | `_on_poll` avg (before → after) | Polls/s achieved | CPU |
|---|---:|---:|---:|
| 10 Hz | ~7.7 ms → 0.5 ms | 10 | ~4 % |
| 100 Hz | ~3.9 ms → 0.3 ms | 100 | ~6 % |
| 1000 Hz | ~11.5 ms → 0.16 ms | ~82 → ~996 | ~9–15 % |

At 1000 Hz the gdbus path could only complete ~82 polls/sec and degraded every
other latency measurement (notes open ~106 ms mean); the X11 path sustains the
full rate with headroom.
