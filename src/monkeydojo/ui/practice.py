"""Practice mode: an action is shown and you press its shortcut.

LazyVim keys are read from the terminal. Omarchy shortcuts never reach the
terminal (Hyprland handles SUPER), so they are caught with a Hyprland submap.

`run` is the loop; what the user sees is up to a view (PlainView here, or the TUI).
"""

import random
import select
import signal
import sys
import time
from contextlib import ExitStack, contextmanager

from monkeydojo import hyprland, keys, learn, real
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
    """Echo keys until they match a sequence or go wrong. Return (ok, seconds, typed)."""
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
                return state == "correct", time.monotonic() - start, typed


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
    """Wait for a shortcut in the Hyprland submap. Return (ok, seconds, combo pressed or None)."""
    by_bind = {hyprland.to_bind_keys(c): c for c in combos}
    verdict, pressed, seconds = trap.ask(list(by_bind), HYPRLAND_TIMEOUT)
    if verdict == "quit":
        raise Quit
    if verdict == "timeout":
        view.timeout()
    if verdict == "ok":
        view.key(by_bind[pressed])
    return verdict == "ok", seconds, pressed


# Seconds a wrong exam answer stays on screen before the next question
EXAM_PAUSE = 1.5


@contextmanager
def keyboard(view, bindings, real_mode=False, block=()):
    """Everything a session needs to read answers. Yield (trap, sandbox).

    Omarchy shortcuts of `bindings` and `block` never run during the session,
    not even between questions or during LazyVim ones.
    """
    # Make sure the submap is removed if the terminal is closed or the process is killed
    def stop(signum, frame):
        raise SystemExit(1)
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, stop)

    with ExitStack() as stack:
        stack.enter_context(view.input_mode(sys.stdin.fileno()))
        sandbox = None
        if real_mode:
            view.message("Setting up the sandbox workspace...")
            sandbox = stack.enter_context(real.Sandbox())
            view.sandbox_ready(sandbox)
        combos = omarchy_combos([*bindings, *block])
        trap = stack.enter_context(hyprland.Trap(combos, block=True)) if combos else None
        yield trap, sandbox


def prepare(view, trap, binding, rng, exclude=()):
    """Return (description, ask, shown, key count, number) for one question."""
    description, answers, n = keys.instantiate(binding, rng, exclude)
    if binding.source == "omarchy":
        answers = keys.hyprland_targets(answers)
        def ask():
            return catch_shortcut(view, trap, answers)
        return description, ask, answers, 1, n
    sequences = keys.targets(binding)
    def ask():
        return read_sequence(view, sys.stdin.fileno(), sequences)
    return description, ask, [" ".join(s) for s in sequences], min(len(s) for s in sequences), n


def answer(view, ask, length, score):
    """Ask once and show the verdict. Return (ok, fast, pressed)."""
    ok, seconds, pressed = ask()
    if not ok:
        score.add(False)
        return False, False, pressed
    limit = keys.fast_limit(length)
    fast = seconds <= limit
    score.add(True, fast, seconds)
    view.right(seconds, limit, fast, score)
    return True, fast, pressed


def run(bindings, progress, save, view=None, forced_level=None, real_mode=False, rng=random, block=()):
    """Ask until the user quits. Return the Score."""
    view = view or PlainView()
    pool, levels = quiz.build_pool(bindings, progress, forced_level, exams=True)
    has_omarchy = any(b.source == "omarchy" for b in bindings)
    has_terminal = any(b.source != "omarchy" for b in bindings)
    view.start(levels, real_mode, has_omarchy, has_terminal)

    score = Score()
    last = None
    with keyboard(view, bindings, real_mode, block) as (trap, sandbox):
        try:
            while True:
                new = learn.next_new(pool, progress)
                binding = new or quiz.pick(learn.known(pool, progress), progress, last)
                last = binding
                # In real mode, switching to the workspace you are on would show nothing
                exclude = {real.current_workspace()} if real_mode and keys.NUMBER in binding.description else ()
                description, ask, shown, length, n = prepare(view, trap, binding, rng, exclude)

                if new:
                    # First time: show the move and press it once, without a score
                    view.intro(binding, description, shown, learn.hints(binding, pool), score, levels)
                    drill(view, ask)
                    if real_mode:
                        real.show(binding, n, sandbox)
                    learn.introduce(progress, binding)
                    save(progress)
                    continue

                view.question(binding, description, score, levels)
                ok, fast, pressed = answer(view, ask, length, score)
                if not ok:
                    mistake = learn.meaning(bindings, binding.source, pressed) if pressed else None
                    view.wrong(shown, score, mistake)
                    drill(view, ask)
                if real_mode:
                    real.show(binding, n, sandbox)

                prog.record_answer(progress, binding, ok, fast)
                save(progress)

                if not forced_level:
                    pool, new_levels = quiz.build_pool(bindings, progress, exams=True)
                    for source, level in new_levels.items():
                        if level > levels[source]:
                            view.unlocked(source, level)
                    levels = new_levels
        except (Quit, KeyboardInterrupt):
            pass

    view.finish(score)
    return score


def exam(bindings, progress, save, view=None, rng=random, block=()):
    """Belt exam: every binding of the current level once, all right and fast.

    A fast right answer counts the binding as learned, even if the exam is failed.
    Return {source: (passed, right, total)}, or {} if there is nothing to examine.
    """
    view = view or PlainView()
    plan = quiz.exam_plan(bindings, progress)
    if not plan:
        return {}
    questions = [b for _, items in plan.values() for b in items]
    rng.shuffle(questions)
    levels = {source: level for source, (level, _) in plan.items()}
    right = dict.fromkeys(plan, 0)
    counts = {source: len(items) for source, (_, items) in plan.items()}

    score = Score()
    # Every shortcut of these sources can be caught, so a wrong one can be named.
    # The start and result screens are inside too, so no shortcut runs at any point.
    with keyboard(view, [b for b in bindings if b.source in plan], block=block) as (trap, _):
        if view.exam_start(levels, counts) is False:
            return {}
        try:
            for binding in questions:
                description, ask, shown, length, _ = prepare(view, trap, binding, rng)
                view.question(binding, description, score, levels)
                ok, fast, pressed = answer(view, ask, length, score)
                if ok and fast:
                    prog.learn_now(progress, binding)
                    right[binding.source] += 1
                else:
                    if not ok:
                        mistake = learn.meaning(bindings, binding.source, pressed) if pressed else None
                        view.wrong(shown, score, mistake)
                    prog.record_answer(progress, binding, ok, fast)
                    save(progress)
                    pause(EXAM_PAUSE)  # time to read the right answer
                save(progress)
        except (Quit, KeyboardInterrupt):
            pass

        results = {}
        for source, (level, items) in plan.items():
            passed = right[source] == len(items)
            if passed:
                prog.pass_exam(progress, source, level)
            results[source] = (passed, right[source], len(items))
        save(progress)
        view.exam_finish(results, levels)
    return results


def pause(seconds):
    """Wait a moment, but stop at once on Ctrl + C or Esc instead of losing the key."""
    if seconds <= 0:
        return
    fd = sys.stdin.fileno()
    end = time.monotonic() + seconds
    while (left := end - time.monotonic()) > 0:
        ready, _, _ = select.select([fd], [], [], left)
        if ready and any(k in (keys.QUIT, "Esc") for k in keyreader.read_keys(fd)):
            raise Quit


def drill(view, ask):
    """After a mistake, press the right shortcut once so the fingers learn it."""
    while True:
        view.drill_prompt()
        ok, *_ = ask()
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

    def intro(self, binding, description, shown, hints, score, levels):
        print(f"{DIM}[{LABELS[binding.source]}]{RESET} {YELLOW}New move:{RESET} {BOLD}{description}{RESET}"
              f" is {' or '.join(shown)}")
        for hint in hints:
            print(f"  {DIM}{hint}{RESET}")

    def wrong(self, shown, score, mistake=None):
        print(f" {RED}✗ It was: {' or '.join(shown)}{RESET}")
        if mistake:
            print(f"  {DIM}what you pressed is: {mistake}{RESET}")

    def drill_prompt(self):
        print(f"  {DIM}now press it:{RESET} ", end="", flush=True)

    def drill_result(self, ok):
        print(f" {GREEN}✓{RESET}\n" if ok else f" {RED}✗{RESET}")

    def unlocked(self, source, level):
        print(f"{YELLOW}{LABELS[source]} {format_level(level)} unlocked!{RESET}\n")

    def exam_start(self, levels, counts):
        print(f"{YELLOW}Belt exam{RESET}")
        for source, level in levels.items():
            print(f"  {LABELS[source]}: {format_level(level)}, {counts[source]} moves")
        print(f"{sum(counts.values())} questions. Get every one right in under 3 s to earn the next belt.")
        print("Ctrl + C or Esc to stop.\n")

    def exam_finish(self, results, levels):
        print()
        for source, (passed, right, total) in results.items():
            verdict = f"{GREEN}passed{RESET}" if passed else f"{RED}not passed{RESET}"
            print(f"{LABELS[source]} {format_level(levels[source])}: {right}/{total}, {verdict}")
        print(f"{DIM}Right answers count as learned either way.{RESET}")

    def finish(self, score):
        print()
        if score.total:
            print(f"\nCorrect: {score.correct}/{score.total}, fast: {score.fast}/{score.total}")
        print("Bye.")
