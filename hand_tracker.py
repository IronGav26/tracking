"""
hand_tracker.py
===============
Tracks a hand in a webcam feed using HSV skin-colour segmentation.

For each frame it computes:
    • normalised X position of the hand centroid   (0.0 – 1.0)
    • normalised Y position of the hand centroid   (0.0 – 1.0)
    • normalised contour area (proxy for depth/z)  (0.0 – 1.0)

These three values are mapped to MIDI CC numbers defined in `cc_map` and
sent via the supplied MidiOutput instance.

Controls (OpenCV window):
    q / Esc  – quit
"""

import cv2
import numpy as np
from collections import deque
from midi_output import MidiOutput


# ── helpers ───────────────────────────────────────────────────────────────────

def _scale_to_midi(value: float) -> int:
    """Map 0.0-1.0 → 0-127 (MIDI CC range)."""
    return int(np.clip(value * 127, 0, 127))


class EMAFilter:
    """Exponential moving average – lightweight 1-D smoother."""
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self._val: float | None = None

    def update(self, new: float) -> float:
        if self._val is None:
            self._val = new
        else:
            self._val = self.alpha * new + (1.0 - self.alpha) * self._val
        return self._val

    def reset(self):
        self._val = None


# ── main class ────────────────────────────────────────────────────────────────

class HandTracker:
    """
    Parameters
    ----------
    lower_hsv : array-like (3,)  Lower HSV bound for skin colour mask.
    upper_hsv : array-like (3,)  Upper HSV bound for skin colour mask.
    camera_index : int           OpenCV camera index (default 0).
    flip : bool                  Mirror the image horizontally.
    cc_map : dict                Maps axis names to MIDI CC numbers.
                                 Keys: "x", "y", "area"
                                 Example: {"x": 1, "y": 2, "area": 11}
    midi : MidiOutput            Configured MIDI output instance.
    smoothing : float            EMA alpha (0 < α ≤ 1). Lower = smoother.
    min_contour_area : int       Ignore blobs smaller than this (px²).
    max_hand_area_ratio : float  Largest expected hand/frame area ratio.
    """

    # HSV display colours
    _COLOUR_BBOX   = (0, 255, 120)
    _COLOUR_CENTRE = (0, 120, 255)
    _COLOUR_TEXT   = (255, 255, 255)

    def __init__(
        self,
        lower_hsv,
        upper_hsv,
        camera_index: int = 0,
        flip: bool = True,
        cc_map: dict | None = None,
        midi: MidiOutput | None = None,
        smoothing: float = 0.3,
        min_contour_area: int = 3_000,
        max_hand_area_ratio: float = 0.35,
    ):
        self.lower_hsv = np.array(lower_hsv, dtype=np.uint8)
        self.upper_hsv = np.array(upper_hsv, dtype=np.uint8)
        self.camera_index = camera_index
        self.flip = flip
        self.cc_map = cc_map or {"x": 1, "y": 2, "area": 11}
        self.midi = midi
        self.min_contour_area = min_contour_area
        self.max_hand_area_ratio = max_hand_area_ratio

        # Per-axis smoothers
        self._smooth = {k: EMAFilter(smoothing) for k in ("x", "y", "area")}

        # Previous CC values – only send on change to reduce MIDI traffic
        self._prev_cc: dict[str, int] = {}

    # ── public API ────────────────────────────────────────────────────────────

    def run(self):
        """Open webcam and process frames until the user quits."""
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.camera_index}")

        print("Hand-to-MIDI running. Press  q  or  Esc  to stop.")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Warning: empty frame received.")
                    continue

                if self.flip:
                    frame = cv2.flip(frame, 1)

                annotated, values = self._process_frame(frame)
                if values and self.midi:
                    self._send_midi(values)

                cv2.imshow("Hand-to-MIDI  [q = quit]", annotated)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):   # q or Esc
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    # ── internals ─────────────────────────────────────────────────────────────

    def _process_frame(self, frame: np.ndarray):
        """
        Detect hand in `frame`, annotate it, and return normalised values.

        Returns
        -------
        annotated : np.ndarray  Frame with overlays drawn.
        values    : dict | None  {"x": float, "y": float, "area": float}
                                 or None if no hand detected.
        """
        h, w = frame.shape[:2]
        frame_area = h * w

        # ── mask ──────────────────────────────────────────────────────────────
        hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)

        # Morphological clean-up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=1)

        # ── find largest contour (assumed = hand) ─────────────────────────────
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)

        annotated = frame.copy()
        values = None

        if contours:
            hand = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(hand)

            if area >= self.min_contour_area:
                # Centroid
                M  = cv2.moments(hand)
                cx = int(M["m10"] / M["m00"]) if M["m00"] else w // 2
                cy = int(M["m01"] / M["m00"]) if M["m00"] else h // 2

                # Bounding box
                x, y, bw, bh = cv2.boundingRect(hand)

                # Normalise
                norm_x    = cx / w
                norm_y    = cy / h  # 0 = top
                norm_area = min(area / (frame_area * self.max_hand_area_ratio), 1.0)

                # Smooth
                sx = self._smooth["x"].update(norm_x)
                sy = self._smooth["y"].update(norm_y)
                sa = self._smooth["area"].update(norm_area)

                values = {"x": sx, "y": sy, "area": sa}

                # ── annotations ──────────────────────────────────────────────
                cv2.drawContours(annotated, [hand], -1, self._COLOUR_BBOX, 2)
                cv2.rectangle(annotated, (x, y), (x + bw, y + bh),
                              self._COLOUR_BBOX, 1)
                cv2.circle(annotated, (cx, cy), 8, self._COLOUR_CENTRE, -1)

                info = (
                    f"X:{sx:.2f}  Y:{sy:.2f}  Area:{sa:.2f}  |  "
                    f"CC{self.cc_map.get('x','?')}:{_scale_to_midi(sx)}  "
                    f"CC{self.cc_map.get('y','?')}:{_scale_to_midi(sy)}  "
                    f"CC{self.cc_map.get('area','?')}:{_scale_to_midi(sa)}"
                )
                cv2.putText(annotated, info, (10, h - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                            self._COLOUR_TEXT, 1, cv2.LINE_AA)
            else:
                self._reset_smoothers()

        # Mask inset (small debug view)
        thumb = cv2.resize(mask, (w // 5, h // 5))
        thumb_bgr = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)
        annotated[0:thumb_bgr.shape[0], 0:thumb_bgr.shape[1]] = thumb_bgr

        # HUD overlay
        cv2.putText(annotated, "Hand-to-MIDI CC Controller",
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    self._COLOUR_TEXT, 1, cv2.LINE_AA)

        return annotated, values

    def _send_midi(self, values: dict):
        """Send CC messages for each mapped axis, only when value changes."""
        for axis, cc_num in self.cc_map.items():
            if axis not in values:
                continue
            midi_val = _scale_to_midi(values[axis])
            if self._prev_cc.get(axis) != midi_val:
                self.midi.send_cc(cc_num, midi_val)
                self._prev_cc[axis] = midi_val

    def _reset_smoothers(self):
        for f in self._smooth.values():
            f.reset()
