"""Plain terminal interface: print and input."""

from monkeydojo import learn, quiz
from monkeydojo import progress as prog
from monkeydojo.levels import LEVEL_NAMES
from monkeydojo.score import Score
from monkeydojo.sources import LABELS

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_prompt(question):
    label = f"{DIM}[{LABELS[question.binding.source]}]{RESET}"
    subject = f"{BOLD}{question.subject}{RESET}"
    if question.kind == "keys_to_action":
        return f"{label} What does {subject} do?"
    return f"{label} What is the shortcut for {subject}?"


def format_level(level):
    return f"level {level} ({LEVEL_NAMES[level - 1]})"


def show_stats(bindings, progress, exams=False):
    for source, items in quiz.by_source(bindings).items():
        print(f"{BOLD}{LABELS[source]}{RESET}")
        unlocked = quiz.unlocked_level(items, progress, exams)
        for level, name in enumerate(LEVEL_NAMES, start=1):
            learned, total = quiz.passed_stats(items, progress, level)
            status = "" if level <= unlocked else f" {DIM}(locked){RESET}"
            if exams and prog.exam_passed(progress, source, level):
                status = f" {GREEN}exam passed{RESET}"
            print(f"  Level {level}  {name:<11} {learned:>3}/{total} learned{status}")


def show_moves(bindings, progress):
    """Every shortcut, by source and level. ✓ marks the ones learned in this progress."""
    for source, levels in quiz.moves_by_level(bindings).items():
        for level, items in levels.items():
            print(f"{BOLD}{LABELS[source]} · level {level} {LEVEL_NAMES[level - 1]}{RESET} {DIM}({len(items)}){RESET}")
            width = max(len(" or ".join(b.keys)) for b in items)
            for b in items:
                mark = f"{GREEN}✓{RESET}" if prog.is_passed(progress, b) else " "
                print(f"  {mark} {' or '.join(b.keys):<{width}}  {b.description}")
            print()


def run(bindings, progress, save, view=None, forced_level=None):
    """Main quiz loop. `save` is called after every answer. Return the Score."""
    view = view or PlainView()
    pool, levels = quiz.build_pool(bindings, progress, forced_level)
    view.start(levels)

    score = Score()
    last = None
    while True:
        new = learn.next_new(pool, progress)
        if new:
            # First time: show the binding before asking about it
            if not view.intro(new, learn.hints(new, pool), levels):
                break
            learn.introduce(progress, new)
            save(progress)
            continue
        binding = quiz.pick(learn.known(pool, progress), progress, last)
        last = binding
        question = quiz.make_question(bindings, binding)
        answer = view.choose(question, score, levels)
        if answer is None:
            break

        is_correct = answer == question.correct_index
        score.add(is_correct)
        mistake = None if is_correct else learn.explain_choice(bindings, question, answer)
        view.result(question, answer, score, mistake)

        prog.record_answer(progress, binding, is_correct)
        save(progress)

        if not forced_level:
            pool, new_levels = quiz.build_pool(bindings, progress)
            for source, level in new_levels.items():
                if level > levels[source]:
                    view.unlocked(source, level)
            levels = new_levels

    view.finish(score)
    return score


class PlainView:
    """print/input, one question after another."""

    def start(self, levels):
        print(f"{YELLOW}Mon-Key Dojo{RESET}")
        for source, level in levels.items():
            print(f"  {LABELS[source]}: {format_level(level)}")
        print("Answer with the option number. Type 'q' to quit.\n")

    def choose(self, question, score, levels):
        """Return the chosen option index, or None to quit."""
        print(format_prompt(question))
        for i, option in enumerate(question.options, start=1):
            print(f"  {i}) {option}")
        valid = [str(i) for i in range(1, len(question.options) + 1)]
        while True:
            try:
                answer = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return None
            if answer in ("q", "quit", "exit"):
                return None
            if answer in valid:
                return int(answer) - 1
            print(f"Please type a number from 1 to {len(valid)}.")

    def intro(self, binding, hints, levels):
        """Show a new binding. Return False to quit."""
        print(f"{DIM}[{LABELS[binding.source]}]{RESET} {YELLOW}New:{RESET} {BOLD}{' or '.join(binding.keys)}{RESET}"
              f" is {BOLD}{binding.description}{RESET}")
        for hint in hints:
            print(f"  {DIM}{hint}{RESET}")
        note = "Just remember it, don't press it"
        if binding.source == "omarchy":
            note += " (here it would really run)"
        print(f"  {YELLOW}{note}.{RESET}")
        try:
            answer = input(f"{DIM}Enter to continue, q to quit{RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        print()
        return answer not in ("q", "quit", "exit")

    def result(self, question, answer, score, mistake=None):
        if answer == question.correct_index:
            print(f"{GREEN}Correct!{RESET}\n")
        else:
            print(f"{RED}Wrong. It was: {question.options[question.correct_index]}{RESET}")
            if mistake:
                print(f"{DIM}{mistake}{RESET}")
            print()

    def unlocked(self, source, level):
        print(f"{YELLOW}{LABELS[source]} {format_level(level)} unlocked!{RESET}\n")

    def finish(self, score):
        if score.total:
            print(f"\nScore: {score.correct}/{score.total} ({score.percent}%)")
        print("Bye.")
