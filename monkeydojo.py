#!/usr/bin/env python3
"""Mon-Key Dojo - a terminal quiz to learn your Omarchy keybindings."""

import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "monkeydojo"
PROGRESS_FILE = DATA_DIR / "progress.json"

# Leitner boxes: 0 = new or failed, MAX_BOX = mastered
MAX_BOX = 5
LEARNED_BOX = 3
UNLOCK_RATIO = 0.8

LEVEL_NAMES = ("Essentials", "Daily use", "Advanced")
LEVELS = (
    {
        "Keybindings", "Omarchy menu", "System menu", "Terminal", "Browser",
        "File manager", "Close window", "Full screen", "Lock system",
        "Toggle window floating/tiling", "Toggle window split",
        "Switch to workspace <number>", "Move window to workspace <number>",
        "Focus on left window", "Focus on right window",
        "Focus on above window", "Focus on below window",
        "Universal copy", "Universal paste", "Screenshot",
    },
    {
        "Apps menu", "Theme menu", "Background switcher", "Clipboard manager",
        "Emojis", "Universal cut", "Screenrecording", "Color picker",
        "Capture menu", "Full width", "Pop window out (float & pin)",
        "Swap window to the left", "Swap window to the right",
        "Swap window up", "Swap window down",
        "Next workspace", "Previous workspace", "Former workspace",
        "Toggle scratchpad", "Move window to scratchpad", "Toggle window grouping",
        "Dismiss last notification", "Dismiss all notifications",
        "Toggle nightlight", "Toggle top bar", "Toggle window transparency",
        "Editor", "Calculator", "Audio", "Bluetooth", "Network", "Power",
    },
)
# Anything not listed above is the last level.

NOISE = ("XF86", "MOUSE", "mouse_")
NUMBERED_KEYS = re.compile(r"^(.*\+ )\d+$")
NUMBERED_DESC = re.compile(r"^(.*\S)\s+\d+$")


def load_bindings():
    """Return a dict of {description: [keys, ...]}, without noisy bindings."""
    try:
        output = subprocess.run(
            ["omarchy", "menu", "keybindings", "--print"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit("Could not read keybindings. Are you running Omarchy?")

    bindings = {}
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
        bindings.setdefault(description, set()).add(keys)
    return {d: sorted(k) for d, k in bindings.items()}


def level_of(description):
    for i, level in enumerate(LEVELS, start=1):
        if description in level:
            return i
    return len(LEVEL_NAMES)


def load_progress():
    """Return a dict of {description: {"box", "seen", "correct"}}."""
    try:
        return json.loads(PROGRESS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_progress(progress):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Write to a temp file first so a crash never leaves a half-written file
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=2))
    tmp.replace(PROGRESS_FILE)


def box(progress, description):
    return progress.get(description, {}).get("box", 0)


def record_answer(progress, description, is_correct):
    entry = progress.setdefault(description, {"box": 0, "seen": 0, "correct": 0})
    entry["seen"] += 1
    if is_correct:
        entry["correct"] += 1
        entry["box"] = min(entry["box"] + 1, MAX_BOX)
    else:
        entry["box"] = 0


def level_stats(bindings, progress, level):
    """Return (learned, total) for a level."""
    items = [d for d in bindings if level_of(d) == level]
    learned = sum(1 for d in items if box(progress, d) >= LEARNED_BOX)
    return learned, len(items)


def unlocked_level(bindings, progress):
    """Highest level the user can practice."""
    for level in range(1, len(LEVEL_NAMES)):
        learned, total = level_stats(bindings, progress, level)
        if learned < UNLOCK_RATIO * total:
            return level
    return len(LEVEL_NAMES)


def pick_description(pool, progress, last):
    """Weighted random pick: lower box = higher chance."""
    choices = [d for d in pool if d != last] or pool
    weights = [2 ** (MAX_BOX - box(progress, d)) for d in choices]
    return random.choices(choices, weights)[0]


def make_question(bindings, description):
    """Return (prompt, options, correct_index)."""
    keys = bindings[description]

    if random.random() < 0.5:
        # Keys -> action. Skip actions that share the key, so only one answer is right.
        key = random.choice(keys)
        prompt = f"What does {BOLD}{key}{RESET} do?"
        others = [d for d in bindings if key not in bindings[d]]
        correct = description
    else:
        # Action -> keys
        prompt = f"What is the shortcut for {BOLD}{description}{RESET}?"
        all_keys = {k for ks in bindings.values() for k in ks}
        others = sorted(all_keys - set(keys))
        correct = random.choice(keys)

    options = [correct] + random.sample(others, 3)
    random.shuffle(options)
    return prompt, options, options.index(correct)


def show_stats(bindings, progress):
    unlocked = unlocked_level(bindings, progress)
    for level, name in enumerate(LEVEL_NAMES, start=1):
        learned, total = level_stats(bindings, progress, level)
        status = "" if level <= unlocked else f" {DIM}(locked){RESET}"
        print(f"Level {level}  {name:<11} {learned:>3}/{total} learned{status}")


def build_pool(bindings, progress, forced_level):
    if forced_level:
        return [d for d in bindings if level_of(d) == forced_level], forced_level
    level = unlocked_level(bindings, progress)
    # Include earlier levels so old bindings keep getting reviewed
    return [d for d in bindings if level_of(d) <= level], level


def main():
    parser = argparse.ArgumentParser(description="Learn your Omarchy keybindings.")
    parser.add_argument("--level", type=int, choices=range(1, len(LEVEL_NAMES) + 1),
                        help="practice only this level")
    parser.add_argument("--stats", action="store_true", help="show your progress and exit")
    parser.add_argument("--reset", action="store_true", help="delete your progress and exit")
    args = parser.parse_args()

    if args.reset:
        PROGRESS_FILE.unlink(missing_ok=True)
        print("Progress reset.")
        return

    bindings = load_bindings()
    progress = load_progress()

    if args.stats:
        show_stats(bindings, progress)
        return

    pool, level = build_pool(bindings, progress, args.level)
    print(f"{YELLOW}Mon-Key Dojo{RESET} - Level {level}: {LEVEL_NAMES[level - 1]}")
    print("Answer with 1-4. Type 'q' to quit.\n")

    correct_count = total = 0
    last = None
    while True:
        description = pick_description(pool, progress, last)
        last = description
        prompt, options, correct = make_question(bindings, description)
        print(prompt)
        for i, option in enumerate(options, start=1):
            print(f"  {i}) {option}")

        try:
            answer = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if answer in ("q", "quit", "exit"):
            break
        if answer not in ("1", "2", "3", "4"):
            print("Please type a number from 1 to 4.\n")
            continue

        total += 1
        is_correct = int(answer) - 1 == correct
        if is_correct:
            correct_count += 1
            print(f"{GREEN}Correct!{RESET}\n")
        else:
            print(f"{RED}Wrong. It was: {options[correct]}{RESET}\n")

        record_answer(progress, description, is_correct)
        save_progress(progress)

        if not args.level:
            new_pool, new_level = build_pool(bindings, progress, None)
            if new_level > level:
                print(f"{YELLOW}Level {new_level} unlocked: {LEVEL_NAMES[new_level - 1]}!{RESET}\n")
                pool, level = new_pool, new_level

    if total:
        print(f"\nScore: {correct_count}/{total} ({correct_count * 100 // total}%)")
    print("Bye.")


if __name__ == "__main__":
    main()
