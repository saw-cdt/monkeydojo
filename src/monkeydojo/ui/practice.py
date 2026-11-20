"""Practice mode: an action is shown and you press its shortcut.

LazyVim keys are read from the terminal. Omarchy shortcuts never reach the
terminal (Hyprland handles SUPER), so they are caught with a Hyprland submap.

`run` is the loop; what the user sees is up to a view (PlainView here, or the TUI).
"""

import random
import signal
import sys
import time
from contextlib import ExitStack

from monkeydojo import hyprland, keys, real
from monkeydojo import progress as prog
from monkeydojo import quiz
from monkeydojo.score import Score
from monkeydojo.sources import LABELS
from monkeydojo.ui import keyreader
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


def read_sequence(view, fd, sequences):
    """Echo keys until they match a sequence or go wrong. Return (ok, seconds)."""
    keyreader.discard_pending(fd)
    typed = []
    start = time.monotonic()
    while True:
        for key in view.read_keys(fd):
            if key == keys.QUIT:
                raise Quit
            typed.append(key)
            view.key(key)
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


def catch_shortcut(view, trap, combos):
    """Wait for a shortcut in the Hyprland submap. Return (ok, seconds)."""
    by_bind = {hyprland.to_bind_keys(c): c for c in combos}
    verdict, pressed, seconds = trap.ask(list(by_bind), HYPRLAND_TIMEOUT)
    if verdict == "quit":
        raise Quit
    if verdict == "timeout":
        view.timeout()
    if verdict == "ok":
        view.key(by_bind[pressed])
    return verdict == "ok", seconds


def run(bindings, progress, save, view=None, forced_level=None, real_mode=False, rng=random):
    """Ask until the user quits. Return the Score."""
    view = view or PlainView()
    fd = sys.stdin.fileno()
    pool, levels = quiz.build_pool(bindings, progress, forced_level)
    has_omarchy = any(b.source == "omarchy" for b in bindings)
    has_terminal = any(b.source != "omarchy" for b in bindings)
    view.start(levels, real_mode, has_omarchy, has_terminal)

    # Make sure the submap is removed if the terminal is closed or the process is killed
    def stop(signum, frame):
        raise SystemExit(1)
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, stop)

    score = Score()
    last = None
    sandbox = None
    with ExitStack() as stack:
        stack.enter_context(view.input_mode(fd))
        if real_mode:
            view.message("Setting up the sandbox workspace...")
            sandbox = stack.enter_context(real.Sandbox())
            view.sandbox_ready(sandbox)
        trap = stack.enter_context(hyprland.Trap(omarchy_combos(bindings))) if has_omarchy else None
        try:
            while True:
                binding = quiz.pick(pool, progress, last)
                last = binding
                # In real mode, switching to the workspace you are on would show nothing
                exclude = {real.current_workspace()} if real_mode and keys.NUMBER in binding.description else ()
                description, answers, n = keys.instantiate(binding, rng, exclude)

                if binding.source == "omarchy":
                    answers = keys.hyprland_targets(answers)
                    def ask(answers=answers):
                        return catch_shortcut(view, trap, answers)
                    shown = answers
                    length = 1
                else:
                    sequences = keys.targets(binding)
                    def ask(sequences=sequences):
                        return read_sequence(view, fd, sequences)
                    shown = [" ".join(s) for s in sequences]
                    length = min(len(s) for s in sequences)

                view.question(binding, description, score, levels)
                ok, seconds = ask()

                fast = False
                if ok:
                    limit = keys.fast_limit(length)
                    fast = seconds <= limit
                    score.add(True, fast, seconds)
                    view.right(seconds, limit, fast, score)
                else:
                    score.add(False)
                    view.wrong(shown, score)
                    drill(view, ask)
                if real_mode:
                    real.show(binding, n, sandbox)

                prog.record_answer(progress, binding, ok, fast)
                save(progress)

                if not forced_level:
                    pool, new_levels = quiz.build_pool(bindings, progress)
                    for source, level in new_levels.items():
                        if level > levels[source]:
                            view.unlocked(source, level)
                    levels = new_levels
        except (Quit, KeyboardInterrupt):
            pass

    view.finish(score)
    return score


def drill(view, ask):
    """After a mistake, press the right shortcut once so the fingers learn it."""
    while True:
        view.drill_prompt()
        ok, _ = ask()
        view.drill_result(ok)
        if ok:
            return


class PlainView:
    """Line by line output, as before the TUI."""

    def input_mode(self, fd):
        return keyreader.key_mode(fd)

    def read_keys(self, fd):
        return keyreader.read_keys(fd)

    def start(self, levels, real_mode, has_omarchy, has_terminal):
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

    def message(self, text):
        print(f"{DIM}{text}{RESET}", flush=True)

    def sandbox_ready(self, sandbox):
        if sandbox.workspace:
            self.message(f"Workspace {sandbox.workspace}, with windows A, B and C around this one."
                         f" You go back to workspace {sandbox.home} when you quit.")
        else:
            self.message("No free workspace found, so practicing here.")

    def question(self, binding, description, score, levels):
        print(f"{DIM}[{LABELS[binding.source]}]{RESET} {BOLD}{description}{RESET}")
        print("> ", end="", flush=True)

    def key(self, name):
        print(name, end=" ", flush=True)

    def timeout(self):
        print(f"{DIM}time's up{RESET}", end=" ")

    def right(self, seconds, limit, fast, score):
        if fast:
            print(f" {GREEN}✓ {seconds:.1f} s{RESET}\n")
        else:
            print(f" {YELLOW}✓ {seconds:.1f} s, slow (aim for {limit:.1f} s){RESET}\n")

    def wrong(self, shown, score):
        print(f" {RED}✗ It was: {' or '.join(shown)}{RESET}")

    def drill_prompt(self):
        print(f"  {DIM}now press it:{RESET} ", end="", flush=True)

    def drill_result(self, ok):
        print(f" {GREEN}✓{RESET}\n" if ok else f" {RED}✗{RESET}")

    def unlocked(self, source, level):
        print(f"{YELLOW}{LABELS[source]} {format_level(level)} unlocked!{RESET}\n")

    def finish(self, score):
        print()
        if score.total:
            print(f"\nCorrect: {score.correct}/{score.total}, fast: {score.fast}/{score.total}")
        print("Bye.")
