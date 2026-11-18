#!/usr/bin/env python3
"""Mon-Key Dojo - a terminal quiz to learn your Omarchy keybindings."""

import random
import subprocess
import sys

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_bindings():
    """Return a dict of {description: [keys, ...]}."""
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
        keys, description = line.split("→", 1)
        keys, description = keys.strip(), description.strip()
        if keys and description:
            bindings.setdefault(description, []).append(keys)
    return bindings


def make_question(bindings):
    """Return (prompt, options, correct_index)."""
    description = random.choice(list(bindings))
    keys = bindings[description]
    others = random.sample([d for d in bindings if d != description], 3)

    if random.random() < 0.5:
        # Keys -> action
        prompt = f"What does {BOLD}{random.choice(keys)}{RESET} do?"
        correct = description
        options = [description] + others
    else:
        # Action -> keys
        prompt = f"What is the shortcut for {BOLD}{description}{RESET}?"
        correct = random.choice(keys)
        options = [correct] + [random.choice(bindings[d]) for d in others]

    random.shuffle(options)
    return prompt, options, options.index(correct)


def main():
    bindings = load_bindings()
    print(f"{YELLOW}Mon-Key Dojo{RESET} - {len(bindings)} actions loaded.")
    print("Answer with 1-4. Type 'q' to quit.\n")

    correct_count = total = 0
    while True:
        prompt, options, correct = make_question(bindings)
        print(prompt)
        for i, option in enumerate(options, start=1):
            print(f"  {i}) {option}")

        answer = input("> ").strip().lower()
        if answer in ("q", "quit", "exit"):
            break
        if answer not in ("1", "2", "3", "4"):
            print("Please type a number from 1 to 4.\n")
            continue

        total += 1
        if int(answer) - 1 == correct:
            correct_count += 1
            print(f"{GREEN}Correct!{RESET}\n")
        else:
            print(f"{RED}Wrong. It was: {options[correct]}{RESET}\n")

    if total:
        print(f"\nScore: {correct_count}/{total} ({correct_count * 100 // total}%)")
    print("Bye.")


if __name__ == "__main__":
    main()
