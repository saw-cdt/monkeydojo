"""Command-line entry point. Connects sources, progress and the UI."""

import argparse
import sys

from monkeydojo import __version__
from monkeydojo import progress as prog
from monkeydojo.levels import LEVEL_NAMES
from monkeydojo.sources import SOURCES, load_all
from monkeydojo.ui import terminal


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="monkeydojo", description="Learn your Omarchy and LazyVim keybindings.")
    parser.add_argument("--source", choices=list(SOURCES),
                        help="practice only this source (default: all)")
    parser.add_argument("--level", type=int, choices=range(1, len(LEVEL_NAMES) + 1),
                        help="practice only this level")
    parser.add_argument("--stats", action="store_true", help="show your progress and exit")
    parser.add_argument("--reset", action="store_true", help="delete your progress and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.reset:
        prog.reset()
        print("Progress reset.")
        return

    bindings, errors = load_all([args.source] if args.source else None)
    for error in errors:
        print(error, file=sys.stderr)
    if not bindings:
        sys.exit("No keybindings found.")

    progress = prog.load()

    if args.stats:
        terminal.show_stats(bindings, progress)
        return

    terminal.run(bindings, progress, save=prog.save, forced_level=args.level)
