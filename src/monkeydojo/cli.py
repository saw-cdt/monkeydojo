"""Command-line entry point. Connects sources, progress and the UI."""

import argparse
import sys

from monkeydojo import __version__
from monkeydojo import hyprland
from monkeydojo import progress as prog
from monkeydojo.levels import LEVEL_NAMES
from monkeydojo.sources import SOURCES, load_all
from monkeydojo.ui import practice, terminal


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="monkeydojo", description="Learn your Omarchy and LazyVim keybindings.")
    parser.add_argument("--source", choices=list(SOURCES),
                        help="practice only this source (default: all)")
    parser.add_argument("--level", type=int, choices=range(1, len(LEVEL_NAMES) + 1),
                        help="practice only this level")
    parser.add_argument("--practice", action="store_true",
                        help="press the shortcut instead of choosing it")
    parser.add_argument("--real", action="store_true",
                        help="practice Omarchy shortcuts and see them happen")
    parser.add_argument("--plain", action="store_true",
                        help="line by line interface instead of the full screen one")
    parser.add_argument("--exam", action="store_true",
                        help="take the belt exam of your current level (practice progress)")
    parser.add_argument("--moves", action="store_true", help="list every shortcut by level and exit")
    parser.add_argument("--stats", action="store_true", help="show your progress and exit")
    parser.add_argument("--reset", action="store_true", help="delete your progress and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    # With no mode chosen, open the menu (the full screen interface)
    if not (args.plain or args.practice or args.real or args.exam or args.moves or args.stats or args.reset) \
            and sys.stdin.isatty() and sys.stdout.isatty():
        from monkeydojo.ui import tui
        tui.main(args.source, args.level)
        return
    if args.real:
        if args.source == "lazyvim":
            sys.exit("Real mode is for Omarchy shortcuts only.")
        args.practice, args.source = True, "omarchy"
    if args.exam:
        args.practice = True

    path = prog.PRACTICE_PATH if args.practice else prog.DEFAULT_PATH

    if args.reset:
        prog.reset(path)
        print("Practice progress reset." if args.practice else "Progress reset.")
        return

    sources = [args.source] if args.source else None
    # Omarchy practice needs a running Hyprland to catch the shortcuts
    hyprland_ok = bool(hyprland.available())
    if args.practice and not hyprland_ok:
        if args.source == "omarchy":
            sys.exit("Omarchy practice needs a running Hyprland session.")
        sources = sources or ["lazyvim"]

    bindings, errors = load_all(sources)
    for error in errors:
        print(error, file=sys.stderr)
    if args.practice:
        bindings = practice.practicable(bindings, hyprland_ok)
    if not bindings:
        sys.exit("No keybindings found.")

    progress = prog.load(path)

    if args.moves:
        terminal.show_moves(bindings, progress)
        return

    if args.stats:
        terminal.show_stats(bindings, progress, exams=args.practice)
        return

    def save(progress):
        prog.save(progress, path)

    if args.practice:
        if not sys.stdin.isatty():
            sys.exit("Practice mode needs an interactive terminal.")
        if args.exam:
            if not practice.exam(bindings, progress, save=save):
                print("Every exam is passed. Nothing left to examine.")
            return
        practice.run(bindings, progress, save=save, forced_level=args.level, real_mode=args.real)
    else:
        terminal.run(bindings, progress, save=save, forced_level=args.level)
