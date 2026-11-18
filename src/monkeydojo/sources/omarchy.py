"""Read bindings from `omarchy menu keybindings --print`."""

import re
import subprocess

from monkeydojo.models import Binding

NOISE = ("XF86", "MOUSE", "mouse_")
NUMBERED_KEYS = re.compile(r"^(.*\+ )\d+$")
NUMBERED_DESC = re.compile(r"^(.*\S)\s+\d+$")


def load():
    result = subprocess.run(
        ["omarchy", "menu", "keybindings", "--print"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "omarchy command failed")
    return parse(result.stdout)


def parse(output):
    """Turn the command output into a list of Binding, without noise."""
    grouped = {}
    for line in output.splitlines():
        # Format: "SUPER + W    → Close window"
        if "→" not in line:
            continue
        keys, description = (part.strip() for part in line.split("→", 1))
        if not keys or not description or any(n in keys for n in NOISE):
            continue
        # "SUPER + 1 → Switch to workspace 1" -> "SUPER + <number> → Switch to workspace <number>"
        if NUMBERED_KEYS.match(keys) and NUMBERED_DESC.match(description):
            keys = NUMBERED_KEYS.sub(r"\1<number>", keys)
            description = NUMBERED_DESC.sub(r"\1 <number>", description)
        grouped.setdefault(description, set()).add(keys)

    return [
        Binding("omarchy", description, tuple(sorted(keys)))
        for description, keys in grouped.items()
    ]
