"""A filler window for the real mode sandbox: shows one big letter.

Usage: python sandbox_window.py LETTER DOJO_PID

It exits as soon as the dojo process is gone, so a crash never leaves windows behind.
"""

import os
import shutil
import sys
import time

COLORS = {"A": "31", "B": "32", "C": "34", "D": "33"}


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def draw(letter):
    columns, lines = shutil.get_terminal_size()
    color = COLORS.get(letter, "37")
    sys.stdout.write("\033[2J\033[?25l")  # clear, hide cursor
    sys.stdout.write(f"\033[{max(lines // 2, 1)};{max(columns // 2, 1)}H\033[1;{color}m{letter}\033[0m")
    sys.stdout.flush()


def main():
    letter, pid = sys.argv[1], int(sys.argv[2])
    try:
        while alive(pid):
            draw(letter)  # redraw also picks up window resizes
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
