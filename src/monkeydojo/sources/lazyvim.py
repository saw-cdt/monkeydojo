"""Read LazyVim keymaps by running Neovim in headless mode."""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from monkeydojo.models import Binding

DUMP_SCRIPT = Path(__file__).with_name("lazyvim_dump.lua")
TIMEOUT = 20

KEY_NAMES = {
    "cr": "Enter", "enter": "Enter", "esc": "Esc", "tab": "Tab", "bs": "Backspace",
    "space": "Space", "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "lt": "<", "bslash": "\\", "bar": "|",
}
MODIFIERS = {"c": "Ctrl", "a": "Alt", "m": "Alt", "s": "Shift"}
TOKEN = re.compile(r"<[^<>]+>|.")
HOTKEY_HINT = re.compile(r"\[(\w)\]")  # "Goto T[y]pe Definition"


def load():
    if not shutil.which("nvim"):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "keymaps.json"
        subprocess.run(
            ["nvim", "--headless", "-c", f"luafile {DUMP_SCRIPT}"],
            env={**os.environ, "MONKEYDOJO_OUT": str(out)},
            capture_output=True, timeout=TIMEOUT,
        )
        if not out.exists():
            raise RuntimeError("Neovim did not write any keymaps")
        data = json.loads(out.read_text())
    return parse(data)


def parse(data):
    """Turn the dump into a list of Binding, without noise."""
    if not data.get("lazyvim"):
        return []
    grouped = {}
    for entry in data.get("maps", []) + data.get("lsp", []):
        lhs, description = entry["lhs"], entry["desc"].strip()
        if is_noise(lhs, description):
            continue
        description = HOTKEY_HINT.sub(r"\1", description)
        grouped.setdefault(description, set()).add(format_keys(lhs))

    return [
        Binding("lazyvim", description, tuple(sorted(keys)))
        for description, keys in grouped.items()
    ]


def is_noise(lhs, description):
    return (
        lhs.startswith(("<Plug>", "<SNR>"))
        or description.startswith((":", "+"))  # built-in commands, which-key groups
        or description.endswith("()")          # raw Lua calls like vim.lsp.buf.rename()
        or description == "which_key_ignore"
    )


def format_keys(lhs):
    """'<leader>ff' or ' ff' -> 'Space f f', '<C-s>' -> 'Ctrl + S'."""
    lhs = re.sub(r"^<leader>", " ", lhs, flags=re.IGNORECASE)
    return " ".join(format_token(t) for t in TOKEN.findall(lhs))


def format_token(token):
    if token == " ":
        return "Space"
    if not (token.startswith("<") and token.endswith(">") and len(token) > 2):
        return token
    parts = token[1:-1].split("-")
    *mods, key = parts if parts[-1] else parts[:-2] + ["-"]
    key = KEY_NAMES.get(key.lower(), key)
    mods = [MODIFIERS.get(m.lower(), m) for m in mods]
    if len(key) == 1 and "Ctrl" in mods:
        key = key.upper()  # Ctrl is case-insensitive in Vim
    return " + ".join(mods + [key])
