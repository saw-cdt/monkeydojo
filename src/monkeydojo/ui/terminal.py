"""Plain terminal interface: print and input."""

from monkeydojo import progress as prog
from monkeydojo import quiz
from monkeydojo.levels import LEVEL_NAMES

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_prompt(question):
    subject = f"{BOLD}{question.subject}{RESET}"
    if question.kind == "keys_to_action":
        return f"What does {subject} do?"
    return f"What is the shortcut for {subject}?"


def show_stats(bindings, progress):
    unlocked = quiz.unlocked_level(bindings, progress)
    for level, name in enumerate(LEVEL_NAMES, start=1):
        learned, total = quiz.level_stats(bindings, progress, level)
        status = "" if level <= unlocked else f" {DIM}(locked){RESET}"
        print(f"Level {level}  {name:<11} {learned:>3}/{total} learned{status}")


def run(bindings, progress, save, forced_level=None):
    """Main quiz loop. `save` is called after every answer."""
    pool, level = quiz.build_pool(bindings, progress, forced_level)
    print(f"{YELLOW}Mon-Key Dojo{RESET} - Level {level}: {LEVEL_NAMES[level - 1]}")
    print("Answer with 1-4. Type 'q' to quit.\n")

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
        if answer not in ("1", "2", "3", "4"):
            print("Please type a number from 1 to 4.\n")
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
            new_pool, new_level = quiz.build_pool(bindings, progress)
            if new_level > level:
                print(f"{YELLOW}Level {new_level} unlocked: {LEVEL_NAMES[new_level - 1]}!{RESET}\n")
                pool, level = new_pool, new_level

    if total:
        print(f"\nScore: {correct_count}/{total} ({correct_count * 100 // total}%)")
    print("Bye.")
