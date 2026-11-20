"""Practice mode: an action is shown and you press its shortcut.

LazyVim keys are read from the terminal. Omarchy shortcuts never reach the
terminal (Hyprland handles SUPER), so they are caught with a Hyprland submap.
"""

import random
import signal
import sys
import time
from contextlib import ExitStack

from monkeydojo import hyprland, keys, real
from monkeydojo import progress as prog
from monkeydojo import quiz
from monkeydojo.sources import LABELS
from monkeydojo.ui.keyreader import discard_pending, key_mode, read_keys
from monkeydojo.ui.terminal import BOLD, DIM, GREEN, RED, RESET, YELLOW, format_level

# Seconds to answer an Omarchy question before the keyboard is given back
HYPRLAND_TIMEOUT = 20


class Quit(Exception):
    pass


def practicable(bindings, hyprland_ok):
    """Bindings that practice mode can check."""
    def ok(b):
        if b.source == "omarchy":
            return hyprland_ok and keys.hyprland_targets(b.keys)
        return keys.targets(b)
    return [b for b in bindings if ok(b)]


def read_sequence(fd, sequences):
    """Echo keys until they match a sequence or go wrong. Return (ok, seconds)."""
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
                return state == "correct", time.monotonic() - start


def omarchy_combos(bindings):
    """Every Omarchy shortcut that can be asked, with <number> filled in, in hl.bind format."""
    combos = set()
    for b in bindings:
        if b.source != "omarchy":
            continue
        for k in keys.hyprland_targets(b.keys):
            digits = "0123456789" if keys.NUMBER in k else "-"
            combos |= {hyprland.to_bind_keys(k.replace(keys.NUMBER, d)) for d in digits}
    return combos


def catch_shortcut(trap, combos):
    """Wait for a shortcut in the Hyprland submap. Return (ok, seconds)."""
    by_bind = {hyprland.to_bind_keys(c): c for c in combos}
    verdict, pressed, seconds = trap.ask(list(by_bind), HYPRLAND_TIMEOUT)
    if verdict == "quit":
        raise Quit
    if verdict == "timeout":
        print(f"{DIM}time's up{RESET}", end=" ")
    if verdict == "ok":
        print(by_bind[pressed], end=" ")
    return verdict == "ok", seconds


def run(bindings, progress, save, forced_level=None, real_mode=False, rng=random):
    fd = sys.stdin.fileno()
    pool, levels = quiz.build_pool(bindings, progress, forced_level)
    has_omarchy = any(b.source == "omarchy" for b in bindings)
    has_terminal = any(b.source != "omarchy" for b in bindings)

    print(f"{YELLOW}Mon-Key Dojo{RESET} {DIM}{'real mode' if real_mode else 'practice'}{RESET}")
    for source, level in levels.items():
        print(f"  {LABELS[source]}: {format_level(level)}")
    print("Press the shortcut for each action.")
    if has_terminal:
        print("Ctrl + C to quit.", end=" ")
    if real_mode:
        print("Esc to quit. A right answer shows the real action for a moment, then undoes it"
              " (menus and window/workspace actions); a wrong one does nothing.", end="")
    elif has_omarchy:
        print("Esc to quit during Omarchy questions; the real action is never run.", end="")
    print("\n")

    # Make sure the submap is removed if the terminal is closed or the process is killed
    def stop(signum, frame):
        raise SystemExit(1)
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, stop)

    total = correct_count = fast_count = 0
    last = None
    sandbox = None
    with ExitStack() as stack:
        stack.enter_context(key_mode(fd))
        if real_mode:
            print(f"{DIM}Setting up the sandbox workspace...{RESET}", flush=True)
            sandbox = stack.enter_context(real.Sandbox())
            if sandbox.workspace:
                print(f"{DIM}Workspace {sandbox.workspace}, with windows A, B and C around this one."
                      f" You go back to workspace {sandbox.home} when you quit.{RESET}\n")
            else:
                print(f"{DIM}No free workspace found, so practicing here.{RESET}\n")
        trap = stack.enter_context(hyprland.Trap(omarchy_combos(bindings))) if has_omarchy else None
        try:
            while True:
                binding = quiz.pick(pool, progress, last)
                last = binding
                # In real mode, switching to the workspace you are on would show nothing
                exclude = {real.current_workspace()} if real_mode and keys.NUMBER in binding.description else ()
                description, answers, n = keys.instantiate(binding, rng, exclude)

                def effect(binding=binding, n=n):
                    if real_mode:
                        real.show(binding, n, sandbox)

                if binding.source == "omarchy":
                    answers = keys.hyprland_targets(answers)
                    def ask(answers=answers):
                        return catch_shortcut(trap, answers)
                    shown = answers
                    length = 1
                else:
                    sequences = keys.targets(binding)
                    def ask(sequences=sequences):
                        return read_sequence(fd, sequences)
                    shown = [" ".join(s) for s in sequences]
                    length = min(len(s) for s in sequences)

                print(f"{DIM}[{LABELS[binding.source]}]{RESET} {BOLD}{description}{RESET}")
                print("> ", end="", flush=True)
                ok, seconds = ask()

                total += 1
                fast = False
                if ok:
                    correct_count += 1
                    limit = keys.fast_limit(length)
                    fast = seconds <= limit
                    if fast:
                        fast_count += 1
                        print(f" {GREEN}✓ {seconds:.1f} s{RESET}\n")
                    else:
                        print(f" {YELLOW}✓ {seconds:.1f} s, slow (aim for {limit:.1f} s){RESET}\n")
                    effect()
                else:
                    print(f" {RED}✗ It was: {' or '.join(shown)}{RESET}")
                    drill(ask)
                    effect()

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


def drill(ask):
    """After a mistake, press the right shortcut once so the fingers learn it."""
    while True:
        print(f"  {DIM}now press it:{RESET} ", end="", flush=True)
        ok, _ = ask()
        if ok:
            print(f" {GREEN}✓{RESET}\n")
            return
        print(f" {RED}✗{RESET}")
