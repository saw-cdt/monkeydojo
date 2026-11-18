"""Where bindings come from. Each source is a module with a load() function.

A source that is not installed returns an empty list instead of failing.
"""

import subprocess

from monkeydojo.sources import lazyvim, omarchy

SOURCES = {
    "omarchy": omarchy.load,
    "lazyvim": lazyvim.load,
}

LABELS = {
    "omarchy": "Omarchy",
    "lazyvim": "LazyVim",
}


def load_all(names=None):
    """Return (bindings, errors). A broken source does not stop the others."""
    bindings, errors = [], []
    for name in names or SOURCES:
        try:
            bindings.extend(SOURCES[name]())
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            errors.append(f"Could not read {LABELS[name]} keybindings: {error}")
    return bindings, errors
