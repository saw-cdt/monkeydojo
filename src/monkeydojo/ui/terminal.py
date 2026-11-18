"""Plain terminal interface: print and input."""

from monkeydojo import progress as prog
from monkeydojo import quiz
from monkeydojo.levels import LEVEL_NAMES
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


def show_stats(bindings, progress):
    for source, items in quiz.by_source(bindings).items():
        print(f"{BOLD}{LABELS[source]}{RESET}")
        unlocked = quiz.unlocked_level(items, progress)
        for level, name in enumerate(LEVEL_NAMES, start=1):
            learned, total = quiz.level_stats(items, progress, level)
            status = "" if level <= unlocked else f" {DIM}(locked){RESET}"
            print(f"  Level {level}  {name:<11} {learned:>3}/{total} learned{status}")


def run(bindings, progress, save, forced_level=None):
    """Main quiz loop. `save` is called after every answer."""
    pool, levels = quiz.build_pool(bindings, progress, forced_level)
    print(f"{YELLOW}Mon-Key Dojo{RESET}")
    for source, level in levels.items():
        print(f"  {LABELS[source]}: {format_level(level)}")
    print("Answer with the option number. Type 'q' to quit.\n")

    correct_count = total = 0
    last = None
    while True:
        binding = quiz.pick(pool, progress, last)
        last = binding
        question = quiz.make_question(bindings, binding)
        print(format_prompt(question))
        for i, option in enumerate(question.options, start=1):
            print(f"  {i}) {option}")

        try:
            answer = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if answer in ("q", "quit", "exit"):
            break
        valid = [str(i) for i in range(1, len(question.options) + 1)]
        if answer not in valid:
            print(f"Please type a number from 1 to {len(valid)}.\n")
            continue

        total += 1
        is_correct = int(answer) - 1 == question.correct_index
        if is_correct:
            correct_count += 1
            print(f"{GREEN}Correct!{RESET}\n")
        else:
            print(f"{RED}Wrong. It was: {question.options[question.correct_index]}{RESET}\n")

        prog.record_answer(progress, binding, is_correct)
        save(progress)

        if not forced_level:
            pool, new_levels = quiz.build_pool(bindings, progress)
            for source, level in new_levels.items():
                if level > levels[source]:
                    print(f"{YELLOW}{LABELS[source]} {format_level(level)} unlocked!{RESET}\n")
            levels = new_levels

    if total:
        print(f"\nScore: {correct_count}/{total} ({correct_count * 100 // total}%)")
    print("Bye.")
