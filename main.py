"""
Hand-to-MIDI CC Controller
==========================
Entry point. Launches the calibration GUI, then starts the
tracking + MIDI loop.

Dependencies:
    pip install opencv-python numpy mido python-rtmidi
"""

import sys
from gui import CalibrationApp
from hand_tracker import HandTracker
from midi_output import MidiOutput
import tkinter as tk


def main():
    # ── 1. Launch calibration / mapping GUI ──────────────────────────────────
    root = tk.Tk()
    app = CalibrationApp(root)
    root.mainloop()

    if not app.confirmed:
        print("Calibration cancelled. Exiting.")
        sys.exit(0)

    config = app.get_config()

    # ── 2. Initialise MIDI output ─────────────────────────────────────────────
    midi = MidiOutput(
        port_name=config["midi_port"],
        channel=config["midi_channel"],
    )

    # ── 3. Initialise hand tracker ────────────────────────────────────────────
    tracker = HandTracker(
        lower_hsv=config["lower_hsv"],
        upper_hsv=config["upper_hsv"],
        camera_index=config["camera_index"],
        flip=config["flip_camera"],
        cc_map=config["cc_map"],      # {axis: cc_number}  e.g. {"x": 1, "y": 2, "area": 11}
        midi=midi,
        smoothing=config["smoothing"],
    )

    # ── 4. Run (blocks until 'q' pressed or window closed) ───────────────────
    try:
        tracker.run()
    finally:
        midi.close()
        print("MIDI port closed. Goodbye.")


if __name__ == "__main__":
    main()
