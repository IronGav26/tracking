# ✋ Hand-to-MIDI CC Controller

Track your hand with a webcam and output real-time MIDI CC signals — usable as an expressive controller for any DAW, synthesizer, or MIDI-compatible software.

---

## Files

| File | Purpose |
|---|---|
| `main.py` | Entry point |
| `gui.py` | Tkinter calibration & MIDI-mapping GUI |
| `hand_tracker.py` | OpenCV hand detection + MIDI dispatch |
| `midi_output.py` | `mido`/`rtmidi` MIDI output wrapper |
| `requirements.txt` | Python dependencies |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> **Windows users:** `python-rtmidi` requires a C++ build toolchain.  
> Install [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/) first,  
> or use a pre-built wheel: `pip install python-rtmidi --only-binary :all:`.

> **Virtual MIDI port (Windows):** Windows doesn't support virtual MIDI ports natively.  
> Install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) and create a port before running.

### 2. Run

```bash
python main.py
```

---

## GUI Workflow

### Tab 1 — 📷 Camera Preview
- A live feed from your webcam is shown.
- **Click on your skin** in the preview — the app samples the HSV colour at that region and automatically sets a generous HSV band around it.
- Adjust the camera index if you have multiple cameras.
- Toggle **Mirror** to flip the image horizontally.

### Tab 2 — 🎨 HSV Mask
- Sliders for **H/S/V min** and **H/S/V max** define the skin colour range.
- A **live blended preview** shows the mask in green overlay — tune until your hand is cleanly highlighted with minimal noise.
- Click **Reset to defaults** to restore the built-in starting values.

### Tab 3 — 🎛️ MIDI Mapping
| Setting | Description |
|---|---|
| MIDI Output Port | The MIDI port to send CC messages to |
| MIDI Channel | Channel 1–16 |
| X position → CC# | CC number driven by hand's left/right position |
| Y position → CC# | CC number driven by hand's up/down position |
| Hand area (Z) → CC# | CC number driven by hand size (proxy for depth) |
| Smoothing (α) | EMA smoothing factor — lower = smoother but laggier |

Click **✔ Confirm & Start** when done.

---

## Tracking Window

After confirming:
- An OpenCV window shows the live feed with tracking overlay.
- A small mask thumbnail is shown in the top-left corner.
- The status bar shows normalised values and current CC values.
- Press **`q`** or **`Esc`** to stop.

---

## MIDI CC Axes

| Axis | Range | Movement |
|---|---|---|
| X | 0–127 | Left edge = 0, Right edge = 127 |
| Y | 0–127 | Top edge = 0, Bottom edge = 127 |
| Area | 0–127 | Small/far hand = 0, Large/close hand = 127 |

Map these in your DAW to any parameter — filter cutoff, reverb send, LFO rate, volume, etc.

---

## Tips

- **Lighting:** Consistent, diffuse front lighting gives the best skin-colour separation.
- **Background:** Avoid backgrounds similar in colour to your skin.
- **Sleeve:** Roll up sleeves or wear a contrasting colour.
- **Click multiple spots** on your hand (palm, back, fingers) to sample a broader range, then widen the S and V sliders slightly.
- If tracking is jittery, lower the **Smoothing α** value (e.g. 0.15).
- If tracking lags too much, raise **Smoothing α** toward 1.0.

---

## Tested Platforms

- macOS 13+ (virtual ports work natively)
- Ubuntu 22.04 (virtual ports work natively)
- Windows 11 (requires loopMIDI)
