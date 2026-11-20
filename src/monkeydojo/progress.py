"""Leitner boxes and the progress file.

Progress is a dict {binding_id: {"box", "seen", "correct"}}.
"""

import json
import os
from pathlib import Path

# 0 = new or failed, MAX_BOX = mastered
MAX_BOX = 5
LEARNED_BOX = 3

FORMAT_VERSION = 2

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "monkeydojo"
DEFAULT_PATH = DATA_DIR / "progress.json"
# Recognizing a shortcut and pressing it are different skills, so they level up apart
PRACTICE_PATH = DATA_DIR / "practice.json"


def box(progress, binding):
    return progress.get(binding.id, {}).get("box", 0)


def is_learned(progress, binding):
    return box(progress, binding) >= LEARNED_BOX


def record_answer(progress, binding, is_correct, fast=True):
    """A right but slow answer counts as correct without moving up a box."""
    entry = progress.setdefault(binding.id, {"box": 0, "seen": 0, "correct": 0})
    entry["seen"] += 1
    if is_correct:
        entry["correct"] += 1
        if fast:
            entry["box"] = min(entry["box"] + 1, MAX_BOX)
    else:
        entry["box"] = 0


def load(path=DEFAULT_PATH):
    try:
        data = json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return _migrate(data)


def save(progress, path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file first so a crash never leaves a half-written file
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": FORMAT_VERSION, "bindings": progress}, indent=2))
    tmp.replace(path)


def reset(path=DEFAULT_PATH):
    Path(path).unlink(missing_ok=True)


def _migrate(data):
    # Version 1 had no "version" key and used plain descriptions (all from Omarchy)
    if "version" not in data:
        return {f"omarchy:{description}": entry for description, entry in data.items()}
    return data["bindings"]
