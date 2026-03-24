"""
midi_output.py
==============
Thin wrapper around `mido` + `python-rtmidi` for sending MIDI CC messages.

Usage
-----
    midi = MidiOutput(port_name="My Synth", channel=0)
    midi.send_cc(cc_number=1, value=64)
    midi.close()

If `port_name` is None or not found, the first available output port is used.
If no ports exist a virtual port named "HandMIDI" is created (Linux/macOS only).
"""

import mido
import mido.backends.rtmidi  # noqa: ensure rtmidi backend is loaded


class MidiOutput:
    """
    Parameters
    ----------
    port_name : str | None  Partial or full name of the desired MIDI output
                            port. Pass None to auto-select.
    channel   : int         MIDI channel 0-15 (0 = Ch 1).
    """

    def __init__(self, port_name: str | None = None, channel: int = 0):
        self.channel = max(0, min(15, channel))
        self._port = self._open_port(port_name)
        print(f"[MIDI] Using port: {self._port.name}  channel: {channel + 1}")

    # ── public ────────────────────────────────────────────────────────────────

    def send_cc(self, cc_number: int, value: int):
        """Send a single Control Change message."""
        msg = mido.Message(
            "control_change",
            channel=self.channel,
            control=max(0, min(127, cc_number)),
            value=max(0, min(127, value)),
        )
        self._port.send(msg)

    def send_note_on(self, note: int, velocity: int = 64):
        msg = mido.Message("note_on", channel=self.channel,
                           note=note, velocity=velocity)
        self._port.send(msg)

    def send_note_off(self, note: int):
        msg = mido.Message("note_off", channel=self.channel,
                           note=note, velocity=0)
        self._port.send(msg)

    def close(self):
        if self._port and not self._port.closed:
            self._port.close()

    @staticmethod
    def list_ports() -> list[str]:
        return mido.get_output_names()

    # ── internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _open_port(port_name: str | None):
        available = mido.get_output_names()

        if available:
            if port_name:
                # Case-insensitive partial match
                for name in available:
                    if port_name.lower() in name.lower():
                        return mido.open_output(name)
                print(f"[MIDI] Port '{port_name}' not found. "
                      f"Available: {available}")

            # Fall back to first port
            print(f"[MIDI] Opening first available port: {available[0]}")
            return mido.open_output(available[0])

        # No ports – try virtual (Linux/macOS)
        print("[MIDI] No output ports found. Creating virtual port 'HandMIDI'.")
        try:
            return mido.open_output("HandMIDI", virtual=True)
        except Exception as exc:
            raise RuntimeError(
                "No MIDI output ports available and virtual ports are not "
                "supported on this platform (Windows). "
                "Please install a virtual MIDI driver such as loopMIDI."
            ) from exc
