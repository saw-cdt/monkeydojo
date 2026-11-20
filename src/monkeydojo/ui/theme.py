"""Colors of the current Omarchy theme that the 16 terminal colors do not have.

The monkey's fur (brown) and face (orange) come from the theme's colors.toml,
converted to the nearest of the 256 terminal colors. Everything else uses the
16 terminal colors, which already follow the theme.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
COLORS_TOML = STATE / "omarchy/current/theme/colors.toml"

# Used when there is no Omarchy theme: a plain brown and orange
DEFAULTS = {"mode": "dark", "brown": "#875f5f", "orange": "#ffaf87"}

_LINE = re.compile(r'^\s*([a-z_]+)\s*=\s*"([^"]*)"')


@dataclass(frozen=True)
class Theme:
    light: bool
    brown: int   # 256-color index
    orange: int


def parse(text):
    """Read the `key = "value"` lines of a colors.toml (no TOML library needed)."""
    values = {}
    for line in text.splitlines():
        match = _LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def load(path=COLORS_TOML):
    try:
        values = parse(Path(path).read_text())
    except OSError:
        values = {}
    get = lambda key: values.get(key) or DEFAULTS[key]
    try:
        brown, orange = to_256(get("brown")), to_256(get("orange"))
    except ValueError:
        brown, orange = to_256(DEFAULTS["brown"]), to_256(DEFAULTS["orange"])
    return Theme(light=get("mode") == "light", brown=brown, orange=orange)


# The 6x6x6 color cube (16-231) and the gray ramp (232-255) of the 256-color palette
_CUBE = (0, 95, 135, 175, 215, 255)


def _palette():
    colors = {}
    for i in range(216):
        r, g, b = _CUBE[i // 36], _CUBE[i // 6 % 6], _CUBE[i % 6]
        colors[16 + i] = (r, g, b)
    for i in range(24):
        v = 8 + 10 * i
        colors[232 + i] = (v, v, v)
    return colors


PALETTE = _palette()


def to_256(hex_color):
    """'#7b5b55' -> the nearest 256-color index (never one of the 16 theme colors)."""
    h = hex_color.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"not a color: {hex_color!r}")
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return min(PALETTE, key=lambda i: sum((a - b) ** 2 for a, b in zip(PALETTE[i], rgb)))
