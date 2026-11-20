"""Read single keypresses from the terminal and name them like the sources do."""

import os
import termios
from contextlib import contextmanager

CTRL_BYTES = {
    0x00: "Ctrl + Space", 0x08: "Ctrl + H", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Esc",
    0x1C: "Ctrl + \\", 0x1D: "Ctrl + ]", 0x1F: "Ctrl + /", 0x7F: "Backspace",
}
CSI_KEYS = {"A": "Up", "B": "Down", "C": "Right", "D": "Left"}
CSI_MODS = {"2": "Shift", "3": "Alt", "5": "Ctrl"}
CSI_PARAMS = "0123456789;:<=>?"
UNKNOWN = "?"


@contextmanager
def key_mode(fd):
    """Read every key as it is pressed: no echo, no line buffering, no signals.

    Output processing stays on, so print() still works normally.
    """
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[0] &= ~(termios.IXON | termios.ICRNL | termios.INLCR | termios.IGNCR)
    new[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG | termios.IEXTEN)
    new[6][termios.VMIN] = 1
    new[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSAFLUSH, new)
    try:
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old)


def discard_pending(fd):
    """Drop keys pressed before the question was shown."""
    termios.tcflush(fd, termios.TCIFLUSH)


def read_keys(fd):
    """Block until the user presses something. Return the key names."""
    # A terminal writes a whole key (even a long escape sequence) in one go,
    # so a lone ESC at the end of a read is the Esc key itself.
    return decode(os.read(fd, 64))


def decode(data):
    text = data.decode(errors="replace")
    keys, i = [], 0
    while i < len(text):
        char = text[i]
        if char == "\x1b" and i + 1 < len(text):
            following = text[i + 1]
            if following == "[":
                j = i + 2
                while j < len(text) and text[j] in CSI_PARAMS:
                    j += 1
                final = text[j] if j < len(text) else ""
                keys.append(_csi(text[i + 2:j], final))
                i = j + 1
            elif following == "O" and i + 2 < len(text):
                keys.append(CSI_KEYS.get(text[i + 2], UNKNOWN))
                i += 3
            else:
                keys.append("Alt + " + _single(following))
                i += 2
            continue
        keys.append(_single(char))
        i += 1
    return keys


def _single(char):
    code = ord(char)
    if code in CTRL_BYTES:
        return CTRL_BYTES[code]
    if 1 <= code <= 26:
        return "Ctrl + " + chr(code + 64)
    if char == " ":
        return "Space"
    return char if char.isprintable() else UNKNOWN


def _csi(params, final):
    """'1;5' + 'A' -> 'Ctrl + Up'."""
    if final == "Z":
        return "Shift + Tab"
    key = CSI_KEYS.get(final)
    if not key:
        return UNKNOWN
    parts = params.split(";")
    if len(parts) < 2:
        return key
    mod = CSI_MODS.get(parts[1])
    return f"{mod} + {key}" if mod else UNKNOWN
