"""Command-line entry point. Connects sources, progress and the UI."""

import argparse
import sys

from monkeydojo import __version__
from monkeydojo import progress as prog
from monkeydojo.levels import LEVEL_NAMES
from monkeydojo.sources import SOURCES, load_all

# Omarchy shortcuts use SUPER, which Hyprland catches before the terminal sees it
PRACTICE_SOURCES = ["lazyvim"]
from monkeydojo.ui import practice, terminal


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="monkeydojo", description="Learn your Omarchy and LazyVim keybindings.")
    parser.add_argument("--source", choices=list(SOURCES),
                        help="practice only this source (default: all)")
    parser.add_argument("--level", type=int, choices=range(1, len(LEVEL_NAMES) + 1),
                        help="practice only this level")
    parser.add_argument("--practice", action="store_true",
                        help="press the shortcut instead of choosing it (LazyVim only for now)")
    parser.add_argument("--stats", action="store_true", help="show your progress and exit")
    parser.add_argument("--reset", action="store_true", help="delete your progress and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    path = prog.PRACTICE_PATH if args.practice else prog.DEFAULT_PATH

    if args.reset:
        prog.reset(path)
        print("Practice progress reset." if args.practice else "Progress reset.")
        return

    sources = [args.source] if args.source else None
    if args.practice:
        if args.source and args.source not in PRACTICE_SOURCES:
            sys.exit(f"Practice mode does not support {args.source} yet.")
        sources = sources or PRACTICE_SOURCES

    bindings, errors = load_all(sources)
    for error in errors:
        print(error, file=sys.stderr)
    if args.practice:
        bindings = practice.typable(bindings)
    if not bindings:
        sys.exit("No keybindings found.")

    progress = prog.load(path)

    if args.stats:
        terminal.show_stats(bindings, progress)
        return

    def save(progress):
        prog.save(progress, path)

    if args.practice:
        if not sys.stdin.isatty():
            sys.exit("Practice mode needs an interactive terminal.")
        practice.run(bindings, progress, save=save, forced_level=args.level)
    else:
        terminal.run(bindings, progress, save=save, forced_level=args.level)
