"""Practice mode: an action is shown and you press its shortcut."""

import sys
import time

from monkeydojo import keys
from monkeydojo import progress as prog
from monkeydojo import quiz
from monkeydojo.sources import LABELS
from monkeydojo.ui.keyreader import discard_pending, key_mode, read_keys
from monkeydojo.ui.terminal import BOLD, DIM, GREEN, RED, RESET, YELLOW, format_level


class Quit(Exception):
    pass


def typable(bindings):
    """Bindings with at least one shortcut a terminal can read."""
    return [b for b in bindings if keys.targets(b)]


def read_sequence(fd, sequences):
    """Echo keys until they match a sequence or go wrong. Return (ok, typed, seconds)."""
    discard_pending(fd)
    typed = []
    start = time.monotonic()
    while True:
        for key in read_keys(fd):
            if key == keys.QUIT:
                raise Quit
            typed.append(key)
            print(key, end=" ", flush=True)
            state = keys.check(typed, sequences)
            if state != "partial":
                return state == "correct", typed, time.monotonic() - start


def run(bindings, progress, save, forced_level=None):
    fd = sys.stdin.fileno()
    pool, levels = quiz.build_pool(bindings, progress, forced_level)
    print(f"{YELLOW}Mon-Key Dojo{RESET} {DIM}practice{RESET}")
    for source, level in levels.items():
        print(f"  {LABELS[source]}: {format_level(level)}")
    print("Press the shortcut for each action. Ctrl + C to quit.\n")

    total = correct_count = fast_count = 0
    last = None
    with key_mode(fd):
        try:
            while True:
                binding = quiz.pick(pool, progress, last)
                last = binding
                sequences = keys.targets(binding)
                print(f"{DIM}[{LABELS[binding.source]}]{RESET} {BOLD}{binding.description}{RESET}")
                print("> ", end="", flush=True)

                ok, typed, seconds = read_sequence(fd, sequences)
                total += 1
                if ok:
                    correct_count += 1
                    limit = keys.fast_limit(typed)
                    fast = seconds <= limit
                    if fast:
                        fast_count += 1
                        print(f" {GREEN}✓ {seconds:.1f} s{RESET}\n")
                    else:
                        print(f" {YELLOW}✓ {seconds:.1f} s, slow (aim for {limit:.1f} s){RESET}\n")
                else:
                    fast = False
                    answer = " or ".join(" ".join(s) for s in sequences)
                    print(f" {RED}✗ It was: {answer}{RESET}")
                    drill(fd, sequences)

                prog.record_answer(progress, binding, ok, fast)
                save(progress)

                if not forced_level:
                    pool, new_levels = quiz.build_pool(bindings, progress)
                    for source, level in new_levels.items():
                        if level > levels[source]:
                            print(f"{YELLOW}{LABELS[source]} {format_level(level)} unlocked!{RESET}\n")
                    levels = new_levels
        except (Quit, KeyboardInterrupt):
            print()

    if total:
        print(f"\nCorrect: {correct_count}/{total}, fast: {fast_count}/{total}")
    print("Bye.")


def drill(fd, sequences):
    """After a mistake, type the right shortcut once so the fingers learn it."""
    while True:
        print(f"  {DIM}now press it:{RESET} ", end="", flush=True)
        ok, _, _ = read_sequence(fd, sequences)
        if ok:
            print(f" {GREEN}✓{RESET}\n")
            return
        print(f" {RED}✗{RESET}")
