# Background alternatives — revision 11

[Side-by-side comparison](comparison.png) · [Notes controls](controls.png)

All three styles were recorded on GNOME/X11 at 2× scaling, with a disposable
sample desktop and notes. Comparisons use the same command-palette animation
(180 ms, startup speed 3) and 58% background opacity. The app defaults to 60%
when no opacity is saved; existing opacity preferences remain unchanged.

| Style | Treatment | Screenshot | Recording |
| --- | --- | --- | --- |
| Dark translucent — default | Uniform cool near-black tint; live desktop remains legible without smearing | [Dark desktop](dim.png), [light desktop](dim-light.png) | [Dark desktop](dim.mp4), [light desktop](dim-light.mp4) |
| Soft spotlight | Lighter near the center, darker at the edges; no blur | [Screenshot](spotlight.png) | [Recording](spotlight.mp4) |
| Blurred desktop | Original cached screenshot blur, retaining its texture | [Screenshot](blur.png) | [Recording](blur.mp4) |

## Findings

The uniform scrim creates the clearest separation from the notes surface on both
light and dark desktops. It leaves desktop geometry stable and avoids both the
smearing and frozen transient UI possible with a captured blur. It is the new
default. Spotlight is a gentler alternative that leaves more context visible near
the panel. Blur is retained as an explicit choice rather than removed.

Dark styles make no desktop-capture calls. The spotlight is rasterized once per
opening, then composited from a cached image. The dark scrim is one rectangle
fill per frame. All use Qt painting, not native window-opacity changes.

The [opening sequence](dim-sequence.png) was decoded from the saved recording
and inspected for the entrance, final settling, and background stability. Notes
remain sharp; the same native surface stays present throughout. Full desktop
recordings can include unrelated tooltips from other running applications.

## Controls

In the Notes menu, choose **Background style (next opening)**, then close and
reopen notes. **Background opacity** changes immediately; 0 hides the effect.
The selection and opacity are saved independently of the animation strategy.
Both sliders continue to ignore arrow keys. Clicking outside notes dismisses
notes and removes its background. Opacity settings are not reset by this update.

## Reproduce

Run from the desktop's X11 session with ffmpeg available:

```sh
QT_QPA_PLATFORM=xcb venv/bin/python tools/record_notes_animation.py /tmp/dim-review --strategy palette --duration 180 --speed 3 --background dim --opacity 58
```

Use `--background spotlight` or `--background blur` to compare alternatives;
`--theme light` checks a light desktop and `--menu` includes the controls. The
script records only its demo run and keeps application data in a temporary folder.
Do not take screenshots inside the animation timer; decode them from the video
afterwards so capture does not interrupt frame pacing.

Automated coverage verifies that dark styles never capture the desktop, that
opacity and spotlight falloff render correctly, and that style changes persist
and apply on the next opening. Existing scaling, blur-edge, mask, animation, and
close/reopen tests remain in place.
