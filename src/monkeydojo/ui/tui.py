"""Full screen interface (curses): the dojo.

A menu with the ninja monkey and your belts, the sessions (quiz, practice, real)
with Session and History panels, a new belt screen and a stats screen.

Keys are read with keyreader, like the plain interface, so practice mode
recognizes exactly the same keys. curses only draws.
"""

import curses
import locale
import os
import select
import signal
import sys
import termios
from collections import deque
from contextlib import nullcontext

from monkeydojo import belts as belt_rules
from monkeydojo import hyprland, keys
from monkeydojo import progress as prog
from monkeydojo import quiz
from monkeydojo.belts import STRIPES
from monkeydojo.levels import LAST_LEVEL, LEVEL_NAMES
from monkeydojo.sources import LABELS, load_all
from monkeydojo.ui import keyreader, ninja, practice, terminal, theme

TITLE = "M O N - K E Y   D O J O"
ENTER = ("Enter", "Ctrl + J")
BACK = ("Esc", "q", "Ctrl + C")
UP = ("Up", "k")
DOWN = ("Down", "j")
LEFT = ("Left", "h")
RIGHT = ("Right", "l")

MODES = {
    "quiz": ("Quiz", "choose what a shortcut does"),
    "practice": ("Practice", "press the shortcut"),
    "real": ("Real", "press it and see it happen"),
    "exam": ("Exam", "all right in 3 s for the next belt"),
    "stats": ("Stats", "your belts and boxes"),
    "moves": ("Moves", "every shortcut by level"),
    "quit": ("Quit", ""),
}

SIDE = 32          # width of the Session and History column
WIDE = 80          # narrower than this, sessions use a single column
COMBO_CHEER = 5    # the monkey cheers every this many right answers in a row


def main(source=None, level=None):
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    curses.wrapper(lambda stdscr: App(stdscr, source, level).run())


def progress_path(mode):
    return prog.DEFAULT_PATH if mode == "quiz" else prog.PRACTICE_PATH


def uses_exams(mode):
    """Practice and real mode win belts with an exam; the quiz by learning."""
    return mode != "quiz"


def stats_key(mode):
    """Records like the best combo are kept per mode, real mode included."""
    return mode


class App:
    def __init__(self, stdscr, source, level):
        self.scr = stdscr
        self.fd = sys.stdin.fileno()
        self.size = None
        self.pending = deque()
        self.draw = lambda: None
        self.source = source
        self.level = level
        self.pairs = {}
        self.rendering = False
        self.dirty = False
        # Redraw as soon as the terminal changes size, even while waiting for
        # Hyprland in real mode (its effects move and resize this window)
        signal.signal(signal.SIGWINCH, self.on_resize)
        self.theme = theme.load()
        curses.raw()
        curses.noecho()
        curses.nonl()
        curses.curs_set(0)
        self.colors = curses.has_colors()
        if self.colors:
            curses.start_color()
            curses.use_default_colors()

    # --- colors ------------------------------------------------------------

    def pair(self, fg, bg=-1):
        """Color pair for (fg, bg), created the first time it is used. -1 is the default."""
        if not self.colors:
            return 0
        key = (fg, bg)
        if key not in self.pairs:
            n = len(self.pairs) + 1
            if n >= curses.COLOR_PAIRS:
                return 0
            curses.init_pair(n, fg, bg)
            self.pairs[key] = n
        return curses.color_pair(self.pairs[key])

    def fg(self, color):
        return self.pair(color)

    @property
    def accent(self):
        return self.fg(curses.COLOR_MAGENTA)

    def belt_color(self, name):
        if name == "white":
            # A white band would vanish on a light theme
            return 8 if self.theme.light and curses.COLORS >= 16 else curses.COLOR_WHITE
        return {"yellow": curses.COLOR_YELLOW, "green": curses.COLOR_GREEN,
                "red": curses.COLOR_RED}[name]

    def role_color(self, role, belt):
        """Terminal color of a ninja pixel, or None for an empty one."""
        rich = curses.COLORS >= 256
        if role == "fur":
            return self.theme.brown if rich else curses.COLOR_RED
        if role == "face":
            return self.theme.orange if rich else curses.COLOR_YELLOW
        if role == "eye":
            # Holes on a dark theme; dark dots on a light one
            return curses.COLOR_BLACK if self.theme.light else None
        if role == "band":
            return self.belt_color(belt)
        if role == "sparkle":
            return curses.COLOR_CYAN
        return None

    # --- drawing -----------------------------------------------------------

    @property
    def width(self):
        return self.size[1]

    @property
    def height(self):
        return self.size[0]

    def fit(self):
        """Follow the terminal size (it changes when real mode moves the window)."""
        size = os.get_terminal_size(self.fd)
        size = (size.lines, size.columns)
        if size != self.size:
            self.size = size
            curses.resizeterm(*size)
            self.scr.clearok(True)  # the terminal may have reflowed what was on screen

    def render(self):
        if self.rendering:
            self.dirty = True  # a resize arrived mid-draw: draw again when done
            return
        self.rendering = True
        try:
            while True:
                self.dirty = False
                self.fit()
                self.scr.erase()
                self.draw()
                self.scr.noutrefresh()
                curses.doupdate()
                if not self.dirty:
                    break
        finally:
            self.rendering = False

    def on_resize(self, signum, frame):
        self.render()

    def put(self, y, x, text, attr=0):
        """Write text, cut at the right edge. Return the column after it."""
        if not 0 <= y < self.height or x >= self.width or x < 0:
            return x + len(text)
        clipped = text[:max(0, self.width - x - (y == self.height - 1))]
        try:
            self.scr.addstr(y, x, clipped, attr)
        except curses.error:
            pass
        return x + len(text)

    def puts(self, y, x, parts):
        """Write several (text, attr) parts one after the other."""
        for text, attr in parts:
            x = self.put(y, x, text, attr)
        return x

    def center(self, y, parts, left=0, width=None):
        width = self.width - left if width is None else width
        total = sum(len(t) for t, _ in parts)
        return self.puts(y, left + max(0, (width - total) // 2), parts)

    def box(self, y, x, h, w, title="", active=False, note=""):
        attr = self.accent if active else self.fg(8 if curses.COLORS >= 16 else curses.COLOR_WHITE) | curses.A_DIM
        if h < 2 or w < 4:
            return
        self.put(y, x, "╭" + "─" * (w - 2) + "╮", attr)
        for row in range(y + 1, y + h - 1):
            self.put(row, x, "│", attr)
            self.put(row, x + w - 1, "│", attr)
        self.put(y + h - 1, x, "╰" + "─" * (w - 2) + "╯", attr)
        if title:
            end = self.put(y, x + 2, title, (self.accent if active else 0) | curses.A_BOLD)
            if note:
                self.put(y, end, "─" + note, curses.A_DIM)

    def draw_ninja(self, y, x, face="calm", belt="white"):
        for row, line in enumerate(ninja.cells(face)):
            for col, (top, bottom) in enumerate(line):
                ct, cb = self.role_color(top, belt), self.role_color(bottom, belt)
                if ct is None and cb is None:
                    continue
                if ct is None:
                    char, attr = "▄", self.pair(cb)
                elif cb is None:
                    char, attr = "▀", self.pair(ct)
                elif ct == cb:
                    char, attr = "█", self.pair(ct)
                else:
                    char, attr = "▀", self.pair(ct, cb)
                self.put(y + row, x + col, char, attr)

    def belt_bar(self, name, width):
        return ("━" * width, self.fg(self.belt_color(name)))

    def stripes(self, b):
        lit = b.stripes
        return [("●" * lit, self.fg(curses.COLOR_YELLOW)), ("○" * (STRIPES - lit), curses.A_DIM)]

    def to_next(self, b):
        """'11/16 to yellow', 'exam for yellow', or 'mastered' at the red belt."""
        if not b.next_name:
            return [(" mastered", self.fg(curses.COLOR_RED) | curses.A_BOLD)]
        if b.exam_ready:
            return [(" exam for ", self.fg(curses.COLOR_YELLOW) | curses.A_BOLD),
                    (b.next_name, self.fg(self.belt_color(b.next_name)))]
        return [(f" {b.learned}/{b.needed} to ", curses.A_DIM),
                (b.next_name, self.fg(self.belt_color(b.next_name)))]

    def chips(self, keys, color):
        parts = []
        for i, key in enumerate(keys):
            if i:
                parts.append((" ", 0))
            parts.append((f" {key} ", self.fg(color) | curses.A_REVERSE | curses.A_BOLD))
        return parts

    # --- input -------------------------------------------------------------

    def read_keys(self, fd=None):
        """Wait for keys, redrawing if the terminal is resized meanwhile."""
        while True:
            ready, _, _ = select.select([self.fd], [], [], 0.2)
            if ready:
                return keyreader.read_keys(self.fd)
            if os.get_terminal_size(self.fd) != (self.size[1], self.size[0]):
                self.render()

    def key(self):
        """Next single key. Keys that arrived together are kept for the next calls."""
        if not self.pending:
            self.pending.extend(self.read_keys())
        return self.pending.popleft()

    def flush_input(self):
        self.pending.clear()
        termios.tcflush(self.fd, termios.TCIFLUSH)

    # --- screens -----------------------------------------------------------

    def run(self):
        self.draw = lambda: (self.draw_ninja(1, 3), self.put(2, 22, "Loading keybindings...", curses.A_DIM))
        self.render()
        self.bindings, self.errors = load_all()
        self.hyprland_ok = bool(hyprland.available())
        menu = Menu(self)
        while True:
            mode = menu.choose()
            if mode == "quit":
                return
            if mode == "stats":
                Stats(self).show()
            elif mode == "moves":
                Moves(self).show()
            else:
                self.session(mode)
            self.flush_input()

    def bindings_for(self, mode, source=None):
        source = "omarchy" if mode == "real" else source
        items = [b for b in self.bindings if source in (None, b.source)]
        if mode in ("practice", "real", "exam"):
            items = practice.practicable(items, self.hyprland_ok)
        return items

    def belts(self, mode):
        """{source: Belt} from the progress of `mode`, for every source.

        Real mode practices Omarchy only and shares the practice progress, so it
        shows the practice belt of Omarchy.
        """
        return belt_rules.belts(self.bindings_for(mode), prog.load(progress_path(mode)), uses_exams(mode))

    def unavailable(self, mode):
        """Why a mode cannot start right now, or None."""
        if mode == "real" and not self.hyprland_ok:
            return "needs Hyprland"
        if mode in MODES and mode not in ("stats", "moves", "quit") and not self.bindings_for(mode, self.source):
            return "no keybindings"
        if mode == "exam" and not quiz.exam_plan(self.bindings_for(mode, self.source),
                                                 prog.load(progress_path(mode))):
            return "every exam passed"
        return None

    def session(self, mode):
        bindings = self.bindings_for(mode, self.source)
        path = progress_path(mode)
        progress = prog.load(path)

        def save(progress):
            prog.save(progress, path)

        if mode == "quiz":
            view = QuizView(self, bindings, progress)
            terminal.run(bindings, progress, save, view, forced_level=self.level)
        elif mode == "exam":
            practice.exam(bindings, progress, save, ExamView(self, bindings, progress))
        else:
            view = PracticeView(self, bindings, progress, mode)
            practice.run(bindings, progress, save, view, forced_level=self.level,
                         real_mode=mode == "real")

    def new_belt(self, source, b):
        """Full screen celebration, until a key is pressed."""
        def draw():
            top = max(1, (self.height - 12) // 2)
            self.draw_ninja(top, (self.width - ninja.WIDTH) // 2, "cheer", b.name)
            color = self.fg(self.belt_color(b.name)) | curses.A_BOLD
            self.center(top + 5, [("✦  NEW BELT  ✦", color)])
            self.center(top + 7, [(LABELS[source], self.fg(curses.COLOR_CYAN) | curses.A_BOLD),
                                  (" · ", 0), (f"{b.name} belt", color)])
            if b.next_name:
                level = b.index + 1
                text = f"level {level} · {LEVEL_NAMES[level - 1]} unlocked"
            else:
                text = "you learned every level"
            self.center(top + 8, [(text, curses.A_DIM)])
            parts = []
            for i, name in enumerate(belt_rules.BELTS):
                if i:
                    parts.append(("  →  ", curses.A_DIM))
                attr = curses.A_BOLD if name == b.name else curses.A_DIM
                parts += [self.belt_bar(name, 4), (f" {name}", attr)]
            self.center(top + 10, parts)
            self.center(self.height - 1, [("any key: keep training", curses.A_DIM)])
        previous = self.draw
        self.draw = draw
        self.flush_input()
        self.render()
        self.key()
        self.draw = previous


class Menu:
    def __init__(self, app):
        self.app = app
        self.rows = ["quiz", "practice", "real", "exam", "stats", "moves", "source", "level", "quit"]
        self.index = 0
        sources = [s for s in LABELS if any(b.source == s for b in app.bindings)]
        self.all_sources = sources
        self.sources = [None] + sources if len(sources) > 1 else sources or [None]
        if app.source not in self.sources:
            app.source = self.sources[0]
        self.levels = [None] + list(range(1, LAST_LEVEL + 1))

    def choose(self):
        app = self.app
        app.draw = self.draw
        while True:
            app.render()
            key = app.key()
            row = self.rows[self.index]
            if key in BACK:
                return "quit"
            if key in UP:
                self.index = (self.index - 1) % len(self.rows)
            elif key in DOWN or key == "Tab":
                self.index = (self.index + 1) % len(self.rows)
            elif key in LEFT + RIGHT and row in ("source", "level"):
                self.change(row, -1 if key in LEFT else 1)
            elif key in ENTER:
                if row in ("source", "level"):
                    self.change(row, 1)
                elif not app.unavailable(row):
                    return row

    def change(self, row, step):
        app = self.app
        if row == "source":
            i = self.sources.index(app.source)
            app.source = self.sources[(i + step) % len(self.sources)]
        else:
            i = self.levels.index(app.level)
            app.level = self.levels[(i + step) % len(self.levels)]

    def mode(self):
        """Mode whose belts the menu shows: the selected one, or practice."""
        row = self.rows[self.index]
        return row if row in ("quiz", "practice", "real") else "practice"

    def draw(self):
        app = self.app
        mode = self.mode()
        belts = app.belts(mode)
        best = belt_rules.best(belts)
        app.draw_ninja(2, 3, "calm", best.name)

        x = 3 + ninja.WIDTH + 4
        app.put(1, x, TITLE, app.accent | curses.A_BOLD)
        app.put(2, x, "─" * len(TITLE), curses.A_DIM)
        app.put(3, x, "learn your keybindings by hand", curses.A_DIM)
        # The rows above the menu never move: one per source, then the best combo
        y = 5
        wide = app.width - x >= 62
        for source in self.all_sources:
            b = belts.get(source)
            if not b:
                why = f"no real mode for {LABELS[source]}" if mode == "real" else "not available in this mode"
                app.puts(y, x, [(f"{LABELS[source]:<8} ", curses.A_DIM), (why, curses.A_DIM)])
                y += 1
                continue
            parts = [(f"{LABELS[source]:<8} ", app.fg(curses.COLOR_CYAN) | curses.A_BOLD)]
            if wide:
                parts += [app.belt_bar(b.name, 8), ("  ", 0)]
            parts += [(f"{b.name + ' belt':<11}", curses.A_BOLD), ("  ", 0), *app.stripes(b)]
            if wide:
                parts += app.to_next(b)
            app.puts(y, x, parts)
            y += 1
        combo = prog.load_stats().get(stats_key(mode), {}).get("best_combo", 0)
        where = MODES[mode][0].lower()
        if combo:
            app.puts(y, x, [("best combo ", curses.A_DIM), (f"×{combo}", app.fg(curses.COLOR_YELLOW) | curses.A_BOLD),
                            (f"  in {where}", curses.A_DIM)])
        else:
            app.put(y, x, f"no combo yet in {where}", curses.A_DIM)
        y += 1

        y = max(y, 7) + 1
        for i, row in enumerate(self.rows):
            selected = i == self.index
            marker = ("▸ ", app.accent | curses.A_BOLD) if selected else ("  ", 0)
            attr = curses.A_BOLD if selected else 0
            if row in ("source", "level"):
                if row == "source":
                    y += 1
                    # Real mode is Omarchy only, whatever the source says
                    value = "Omarchy" if self.rows[self.index] == "real" else LABELS.get(app.source, "All")
                else:
                    value = f"{app.level} {LEVEL_NAMES[app.level - 1]}" if app.level else "Auto"
                app.puts(y, 4, [marker, (f"{row.title():<10}", curses.A_DIM | attr),
                                (f"‹ {value} ›", app.fg(curses.COLOR_CYAN) | attr)])
            else:
                if row == "quit":
                    y += 1
                name, hint = MODES[row]
                reason = app.unavailable(row)
                app.puts(y, 4, [marker, (f"{name:<10}", attr | (curses.A_DIM if reason else 0)),
                                (reason or hint, curses.A_DIM)])
            y += 1

        app.puts(app.height - 1, 2, [("↑↓", app.accent), (" move   ", curses.A_DIM),
                                     ("←→", app.accent), (" change   ", curses.A_DIM),
                                     ("enter", app.accent), (" start   ", curses.A_DIM),
                                     ("q", app.accent), (" quit", curses.A_DIM)])
        if app.errors:
            app.put(app.height - 2, 2, app.errors[0], app.fg(curses.COLOR_RED))


def draw_progress(app, top, x, mode, bindings):
    """Belt and level bars per source for the progress of `mode`."""
    progress = prog.load(progress_path(mode))
    width = max(6, min(20, app.width - x - 26))
    y = top
    for source, items in quiz.by_source(bindings).items():
        b = belt_rules.belt(items, progress, uses_exams(mode))
        unlocked = quiz.unlocked_level(items, progress, uses_exams(mode))
        app.puts(y, x, [(f"{LABELS[source]:<9}", app.fg(curses.COLOR_CYAN) | curses.A_BOLD),
                        app.belt_bar(b.name, 6), (f"  {b.name} belt", curses.A_BOLD)])
        y += 1
        for level in range(1, LAST_LEVEL + 1):
            learned, total = quiz.level_stats(items, progress, level)
            locked = level > unlocked
            attr = curses.A_DIM if locked else 0
            filled = round(width * learned / total) if total else 0
            app.puts(y, x, [(f"{level} {LEVEL_NAMES[level - 1]:<10} ", attr),
                            ("█" * filled, curses.A_DIM if locked else app.fg(curses.COLOR_GREEN)),
                            ("░" * (width - filled), curses.A_DIM),
                            (f" {learned}/{total}" + (" locked" if locked else ""), attr),
                            (" exam ✓" if uses_exams(mode) and prog.exam_passed(progress, source, level) else "",
                             app.fg(curses.COLOR_GREEN))])
            y += 1
        y += 1
    return y


class Stats:
    def __init__(self, app):
        self.app = app
        self.mode = "practice"

    def show(self):
        app = self.app
        app.draw = self.draw
        while True:
            app.render()
            key = app.key()
            if key in BACK or key in ENTER:
                return
            if key in LEFT + RIGHT or key == "Tab":
                self.mode = "quiz" if self.mode == "practice" else "practice"

    def draw(self):
        app = self.app
        app.put(0, 2, "Stats", app.accent | curses.A_BOLD)
        x = 2
        for mode, name in (("quiz", "Quiz"), ("practice", "Practice")):
            on = mode == self.mode
            attr = (app.accent | curses.A_BOLD | curses.A_REVERSE) if on else curses.A_DIM
            x = app.put(2, x, f" {name} ", attr) + 1
        bindings = app.bindings_for(self.mode)
        y = draw_progress(app, 4, 2, self.mode, bindings)

        progress = prog.load(progress_path(self.mode))
        if y + len(quiz.by_source(bindings)) < app.height - 1:
            app.put(y, 2, "Boxes (0 new, 3+ learned)", curses.A_BOLD)
            y += 1
            for source, items in quiz.by_source(bindings).items():
                counts = [0] * (prog.MAX_BOX + 1)
                for b in items:
                    counts[prog.box(progress, b)] += 1
                cells = "  ".join(f"{i}:{n}" for i, n in enumerate(counts))
                app.put(y, 2, f"{LABELS[source]:<8} {cells}")
                y += 1
        app.puts(app.height - 1, 2, [("←→", app.accent), (" quiz/practice   ", curses.A_DIM),
                                     ("q", app.accent), (" back", curses.A_DIM)])


class SessionView:
    """What quiz and practice sessions share: panels, belts, combo and history."""

    def __init__(self, app, bindings, progress, mode):
        self.app = app
        self.bindings = bindings
        self.progress = progress
        self.mode = mode
        self.levels = {}
        self.score = None
        self.notice = None
        self.face = "ready"
        self.source = None
        self.history = deque(maxlen=40)  # (text, attr)
        self.belts = belt_rules.belts(bindings, progress, uses_exams(mode))
        self.stats = prog.load_stats()
        self.best_combo = self.stats.get(stats_key(mode), {}).get("best_combo", 0)
        self.record_told = False

    def input_mode(self, fd):
        return nullcontext()

    def read_keys(self, fd):
        return self.app.read_keys(fd)

    def message(self, text):
        self.waiting = text
        self.app.render()

    def sandbox_ready(self, sandbox):
        pass  # the dojo just starts; the plain interface explains the sandbox

    def unlocked(self, source, level):
        pass  # belts are checked before each question, see check_belts

    def check_belts(self):
        """Show the new belt screen for every source that just earned one."""
        new = belt_rules.belts(self.bindings, self.progress, uses_exams(self.mode))
        for source, b in new.items():
            if b.index > self.belts[source].index:
                self.app.new_belt(source, b)
            elif b.exam_ready and not self.belts[source].exam_ready and self.mode != "exam":
                self.notice = (f"{LABELS[source]} exam ready! take it from the menu",
                               self.app.fg(curses.COLOR_YELLOW) | curses.A_BOLD)
        self.belts = new
        self.app.draw = self.draw

    def after_answer(self, ok):
        """Combo bookkeeping and the monkey's face after an answer."""
        app = self.app
        s = self.score
        if not ok:
            self.face = "sad"
            return
        if s.streak and s.streak % COMBO_CHEER == 0:
            self.face = "cheer"
            self.notice = (f"combo ×{s.streak}!", app.fg(curses.COLOR_YELLOW) | curses.A_BOLD)
        else:
            self.face = "happy"
        if self.best_combo and s.streak > self.best_combo and not self.record_told:
            self.record_told = True
            self.face = "cheer"
            self.notice = (f"new best combo! ×{s.streak}", app.fg(curses.COLOR_YELLOW) | curses.A_BOLD)

    def move_chips(self, shown):
        parts = []
        for i, combo in enumerate(shown):
            if i:
                parts.append(("  or  ", curses.A_DIM))
            # An Omarchy shortcut is one chord; a LazyVim one can be a sequence of keys
            tokens = [combo] if self.source == "omarchy" else keys.split_keys(combo)
            parts += self.app.chips(tokens, curses.COLOR_GREEN)
        return parts

    def belt_of(self, source):
        return self.belts.get(source) or belt_rules.Belt(0, 0, 0)

    # --- drawing -----------------------------------------------------------

    def session_lines(self):
        app = self.app
        s = self.score
        combo = s.streak if s else 0
        best = max(self.best_combo, s.best_streak if s else 0)
        combo_attr = (app.fg(curses.COLOR_YELLOW) | curses.A_BOLD) if combo >= 3 else curses.A_BOLD
        lines = [[("Combo     ", curses.A_DIM), (f"×{combo}", combo_attr), (f"   best {best}", curses.A_DIM)]]
        if s and s.total:
            lines.append([("Correct   ", curses.A_DIM), (f"{s.correct}/{s.total}", curses.A_BOLD),
                          (f"  {s.percent}%", curses.A_DIM)])
            if self.mode != "quiz":
                lines.append([("Fast      ", curses.A_DIM), (str(s.fast), curses.A_BOLD)])
                if s.average is not None:
                    lines.append([("Average   ", curses.A_DIM), (f"{s.average:.1f} s", curses.A_BOLD)])
        lines.append([])
        for source, b in self.belts.items():
            lines.append([(f"{LABELS[source]:<8}", app.fg(curses.COLOR_CYAN)), app.belt_bar(b.name, 4),
                          (" ", 0), *app.stripes(b), (f" {b.learned}/{b.needed}" if b.needed else "", curses.A_DIM)])
        return lines

    def draw_history(self, y, x, bottom, width):
        """Last answers, newest first, cut to fit inside the panel."""
        for i, (text, attr) in enumerate(self.history):
            if y >= bottom:
                break
            if len(text) > width:
                text = text[:width - 1] + "…"
            self.app.put(y, x, text, attr if i == 0 else attr | curses.A_DIM)
            y += 1

    def draw_frame(self, title, note, hint):
        """Panels around the stage. Return (top, left, width, bottom) of the stage."""
        app = self.app
        h, w = app.height, app.width
        if w >= WIDE and h >= 18:
            lines = self.session_lines()
            side_h = min(len(lines) + 3, h - 6)
            app.box(0, 0, side_h, SIDE, "Session")
            for i, parts in enumerate(lines[:side_h - 2]):
                app.puts(1 + i, 2, parts)
            app.box(side_h, 0, h - 1 - side_h, SIDE, "History")
            self.draw_history(side_h + 1, 2, h - 2, SIDE - 4)
            app.box(0, SIDE, h - 1, w - SIDE, title, active=True, note=note)
            stage = (1, SIDE + 1, w - SIDE - 2, h - 2)
        else:
            # One column: stage, a short history, then the score line
            hist_h = 5 if h >= 18 else 0
            stage_h = h - 2 - hist_h
            app.box(0, 0, stage_h, w, title, active=True, note=note)
            if hist_h:
                app.box(stage_h, 0, hist_h, w, "History")
                self.draw_history(stage_h + 1, 2, stage_h + hist_h - 1, w - 4)
            s = self.score
            parts = [("combo ", curses.A_DIM), (f"×{s.streak if s else 0}", app.fg(curses.COLOR_YELLOW) | curses.A_BOLD)]
            if s and s.total:
                parts += [(f"   ✓ {s.correct}/{s.total}", app.fg(curses.COLOR_GREEN))]
            if self.source:
                b = self.belt_of(self.source)
                parts += [("   ", 0), app.belt_bar(b.name, 4), (" ", 0), *app.stripes(b)]
            app.puts(h - 2, 1, parts)
            stage = (1, 1, w - 2, stage_h - 1)
        app.put(h - 1, 2, hint, curses.A_DIM)
        return stage

    def draw_head(self, top, left, width, bottom, title):
        """The monkey, the source and the question. Return the row below them.

        With room they are stacked in the middle. On a short stage (real mode's
        quarter of the screen) the monkey goes left with the source beside it,
        and the question gets its own line below.
        """
        app = self.app
        band = self.belt_of(self.source).name if self.source else "white"
        source = [(LABELS[self.source].upper(), curses.A_DIM | curses.A_BOLD)] if self.source else []
        if bottom - top >= 14:
            y = top + 2
            if self.notice:
                app.center(y - 1, [self.notice], left, width)
            # Center the face; the headband tails stick out to the right
            app.draw_ninja(y, left + (width - ninja.FACE_WIDTH) // 2, self.face, band)
            y += ninja.HEIGHT + 1
            if title:
                app.center(y, source, left, width)
                app.center(y + 2, title, left, width)
            return y + 4
        x = left + 2
        app.draw_ninja(top, x, self.face, band)
        tx = x + ninja.WIDTH + 2
        app.puts(top + 1, tx, source)
        if self.notice:
            app.puts(top + 2, tx, [self.notice])
        y = top + ninja.HEIGHT
        if title:
            app.center(y, title, left, width)
        return y + 1

    def question_title(self, text):
        """The question as a highlighted band, so it is the first thing you read."""
        return [(f"  {text}  ", self.app.accent | curses.A_REVERSE | curses.A_BOLD)]

    def draw_belt_row(self, y, left, width):
        if not self.source:
            return
        app = self.app
        b = self.belt_of(self.source)
        parts = [(f"{LABELS[self.source]}  ", app.fg(curses.COLOR_CYAN) | curses.A_BOLD),
                 app.belt_bar(b.name, 10), (f"  {b.name} belt   ", curses.A_DIM), *app.stripes(b), *app.to_next(b)]
        app.center(y, parts, left, width)

    def finish(self, score):
        app = self.app
        self.score = score
        new_record = prog.record_combo(self.stats, stats_key(self.mode), score.best_streak)
        if new_record:
            prog.save_stats(self.stats)
        self.check_belts()
        if not score.total:
            return
        app.flush_input()

        def draw():
            top = max(1, (app.height - 12) // 2)
            app.draw_ninja(top, (app.width - ninja.WIDTH) // 2, "cheer" if score.percent >= 80 else "calm",
                           belt_rules.best(self.belts).name)
            app.center(top + 5, [("Session over", curses.A_BOLD)])
            rows = [[("Correct      ", curses.A_DIM), (f"{score.correct}/{score.total} ({score.percent}%)", 0)],
                    [("Best combo   ", curses.A_DIM), (f"×{score.best_streak}", app.fg(curses.COLOR_YELLOW) | curses.A_BOLD),
                     ("  new record!" if new_record and score.best_streak > 1 else "", app.fg(curses.COLOR_YELLOW))]]
            if self.mode != "quiz":
                rows.append([("Fast         ", curses.A_DIM), (f"{score.fast}/{score.total}", 0)])
                if score.average is not None:
                    rows.append([("Average      ", curses.A_DIM), (f"{score.average:.1f} s", 0)])
            x = max(2, (app.width - 32) // 2)
            for i, parts in enumerate(rows):
                app.puts(top + 7 + i, x, parts)
            app.center(app.height - 1, [("any key: back to the menu", curses.A_DIM)])
        app.draw = draw
        app.render()
        app.key()


class PracticeView(SessionView):
    def __init__(self, app, bindings, progress, mode):
        super().__init__(app, bindings, progress, mode)
        self.description = ""
        self.typed = []
        self.result = None   # parts under the typed keys
        self.drilling = False
        self.drill_from = 0
        self.introducing = False
        self.hints = []
        self.mistake = None
        self.has_terminal = False
        self.waiting = "Getting ready..."

    def start(self, levels, real_mode, has_omarchy, has_terminal):
        self.levels = levels
        self.has_terminal = has_terminal
        self.app.draw = self.draw
        self.app.render()

    def question(self, binding, description, score, levels):
        self.score = score
        if self.mode == "real":
            # Real effects move and resize this window; repaint everything
            self.app.scr.clearok(True)
        self.check_belts()
        self.source = binding.source
        self.description = description
        self.levels = levels
        self.typed = []
        self.result = None
        self.drilling = False
        self.drill_from = 0
        self.introducing = False
        self.hints = []
        self.mistake = None
        self.waiting = None
        self.app.render()

    def frame_note(self):
        level = next(iter(self.levels.values()), 1)
        return f"level {level} {LEVEL_NAMES[level - 1]}"

    def intro(self, binding, description, shown, hints, score, levels):
        """A binding you have never seen: show it, then press it once."""
        app = self.app
        self.question(binding, description, score, levels)
        self.introducing = True
        self.hints = hints
        self.face = "calm"
        self.notice = None
        self.result = [("new move  ", app.fg(curses.COLOR_YELLOW) | curses.A_BOLD), *self.move_chips(shown)]
        self.history.appendleft((f"★       {description}", app.fg(curses.COLOR_YELLOW)))
        app.render()

    def key(self, name):
        self.typed.append(name)
        self.app.render()

    def timeout(self):
        self.result = [("time's up", curses.A_DIM)]

    def right(self, seconds, limit, fast, score):
        app = self.app
        color = curses.COLOR_GREEN if fast else curses.COLOR_YELLOW
        self.result = [(f"✓ {seconds:.1f} s", app.fg(color) | curses.A_BOLD),
                       ("  clean strike" if fast else f"  slow, aim for {limit:.1f} s", curses.A_DIM)]
        self.history.appendleft((f"✓ {seconds:4.1f}  {self.description}", app.fg(color)))
        self.notice = None
        self.after_answer(True)
        app.render()

    def wrong(self, shown, score, mistake=None):
        app = self.app
        self.result = [("✗ the move is  ", app.fg(curses.COLOR_RED)), *self.move_chips(shown)]
        self.mistake = mistake
        self.history.appendleft((f"✗       {self.description}", app.fg(curses.COLOR_RED)))
        self.notice = None
        self.after_answer(False)
        app.render()

    def drill_prompt(self):
        self.drilling = True
        self.drill_from = len(self.typed)
        self.app.render()

    def drill_result(self, ok):
        if not ok:
            self.drill_from = len(self.typed)  # try again from a clean line
        self.app.render()

    def draw(self):
        app = self.app
        quit_keys = []
        if self.has_terminal:
            quit_keys.append("ctrl+c")
        if "omarchy" in self.levels:
            quit_keys.append("esc (Omarchy)")
        top, left, width, bottom = self.draw_frame(MODES[self.mode][0], self.frame_note(),
                                                   " / ".join(quit_keys) + ": back to the menu")
        if self.waiting:
            y = self.draw_head(top, left, width, bottom, None)
            app.center(y, [(self.waiting, curses.A_DIM)], left, width)
            return
        y = self.draw_head(top, left, width, bottom, self.question_title(self.description))
        first = self.typed[:self.drill_from] if self.drilling else self.typed
        typed_color = curses.COLOR_WHITE
        if self.result:
            typed_color = curses.COLOR_RED if self.face == "sad" else curses.COLOR_GREEN
        roomy = bottom - top >= 14
        if self.introducing:
            app.center(y, self.result, left, width)
            y += 2 if roomy else 1
            # Hints only where they fit; the line to press it on matters more
            for hint in self.hints:
                if y >= bottom - (2 if roomy else 1):
                    break
                if len(hint) > width - 2:
                    hint = hint[:width - 3] + "…"
                app.center(y, [(hint, curses.A_DIM)], left, width)
                y += 1
            y += 1 if roomy and self.hints else 0
        else:
            app.center(y, app.chips(first, typed_color) if first else [("…", curses.A_DIM)], left, width)
            y += 2 if roomy else 1
            if self.result:
                app.center(y, self.result, left, width)
                y += 1
                if self.mistake and y < bottom - 1:
                    text = f"you pressed: {self.mistake}"
                    app.center(y, [(text[:width - 2], curses.A_DIM)], left, width)
                    y += 1
                y += 1 if roomy else 0
        if self.drilling:
            again = self.typed[self.drill_from:]
            label = "press it: " if self.introducing else "again: "
            app.center(y, [(label, app.fg(curses.COLOR_YELLOW)), *app.chips(again, curses.COLOR_WHITE),
                           (" █", 0)], left, width)
        if bottom - y > 3:
            self.draw_belt_row(bottom - 1, left, width)


class QuizView(SessionView):
    def __init__(self, app, bindings, progress):
        super().__init__(app, bindings, progress, "quiz")
        self.current = None
        self.selected = 0
        self.answer = None
        self.card = None     # (binding, hints) while a new binding is shown
        self.mistake = None

    def start(self, levels):
        self.levels = levels
        self.app.draw = self.draw

    def choose(self, question, score, levels):
        self.score = score
        self.check_belts()
        self.current, self.levels = question, levels
        self.source = question.binding.source
        self.selected, self.answer, self.mistake = 0, None, None
        app = self.app
        while True:
            app.render()
            key = app.key()
            if key in BACK:
                return None
            if key in UP:
                self.selected = (self.selected - 1) % len(question.options)
            elif key in DOWN or key == "Tab":
                self.selected = (self.selected + 1) % len(question.options)
            elif key in ENTER:
                return self.selected
            elif key.isdigit() and 1 <= int(key) <= len(question.options):
                return int(key) - 1

    def intro(self, binding, hints, levels):
        """A binding you have never seen, before it is asked. Return False to quit."""
        app = self.app
        self.check_belts()
        self.current, self.levels = None, levels
        self.source = binding.source
        self.face, self.notice = "calm", None
        self.card = (binding, hints)
        self.history.appendleft((f"★ {binding.description}", app.fg(curses.COLOR_YELLOW)))
        app.flush_input()
        # Only Enter goes on, so trying the shortcut does not skip the card
        while True:
            app.render()
            key = app.key()
            if key in ENTER or key in BACK:
                break
        self.card = None
        return key not in BACK

    def result(self, question, answer, score, mistake=None):
        app = self.app
        self.mistake = mistake
        correct = question.options[question.correct_index]
        self.notice = None
        ok = answer == question.correct_index
        self.history.appendleft((f"{'✓' if ok else '✗'} {question.subject}  →  {correct}",
                                 app.fg(curses.COLOR_GREEN if ok else curses.COLOR_RED)))
        self.after_answer(ok)
        if ok:
            return
        # Show the right option before moving on
        self.answer = answer
        app.render()
        app.flush_input()
        app.key()

    def draw(self):
        app = self.app
        hint = "1-4 or ↑↓ enter: answer   q: back to the menu"
        if self.answer is not None:
            hint = "any key: next question"
        if self.card:
            hint = "enter: got it   q: back to the menu"
        level = next(iter(self.levels.values()), 1)
        top, left, width, bottom = self.draw_frame("Quiz", f"level {level} {LEVEL_NAMES[level - 1]}", hint)
        if self.card:
            self.draw_card(top, left, width, bottom)
            return
        q = self.current
        if not q:
            self.draw_head(top, left, width, bottom, None)
            return
        subject = (q.subject, app.fg(curses.COLOR_CYAN) | curses.A_BOLD)
        if q.kind == "keys_to_action":
            title = [("What does ", 0), subject, (" do?", 0)]
        else:
            title = [("Shortcut for ", 0), subject, ("?", 0)]
        y = self.draw_head(top, left, width, bottom, title)
        x = left + max(1, (width - max(len(o) for o in q.options) - 6) // 2)
        for i, option in enumerate(q.options):
            attr = 0
            if self.answer is not None:
                if i == q.correct_index:
                    attr = app.fg(curses.COLOR_GREEN) | curses.A_BOLD
                elif i == self.answer:
                    attr = app.fg(curses.COLOR_RED)
                else:
                    attr = curses.A_DIM
            elif i == self.selected:
                attr = app.accent | curses.A_BOLD
            marker = "▸" if i == self.selected and self.answer is None else " "
            app.put(y + i, x, f"{marker} {i + 1}) {option}", attr)
        if self.mistake and y + len(q.options) + 1 < bottom:
            app.center(y + len(q.options) + 1, [(self.mistake[:width - 2], curses.A_DIM)], left, width)
        if bottom - (y + len(q.options)) > 3:
            self.draw_belt_row(bottom - 1, left, width)

    def draw_card(self, top, left, width, bottom):
        """A new binding: what it does, its keys and its family."""
        app = self.app
        binding, hints = self.card
        title = [("new shortcut  ", app.fg(curses.COLOR_YELLOW) | curses.A_BOLD),
                 (binding.description, app.fg(curses.COLOR_CYAN) | curses.A_BOLD)]
        y = self.draw_head(top, left, width, bottom, title)
        app.center(y, self.move_chips(binding.keys), left, width)
        y += 2
        # In the quiz nothing catches the keys, so an Omarchy shortcut would really run
        note = "just remember it, don't press it"
        if binding.source == "omarchy":
            note += ": here it would really run"
        app.center(y, [(note, app.fg(curses.COLOR_YELLOW))], left, width)
        y += 2
        for hint in hints:
            if y >= bottom - 1:
                break
            if len(hint) > width - 2:
                hint = hint[:width - 3] + "…"
            app.center(y, [(hint, curses.A_DIM)], left, width)
            y += 1


class ExamView(PracticeView):
    """A belt exam: the practice screen with a counter, a start screen and the results."""

    def __init__(self, app, bindings, progress):
        super().__init__(app, bindings, progress, "exam")
        self.counts = {}
        self.asked = 0

    def exam_start(self, levels, counts):
        """Say what the exam is about. Return False to go back to the menu."""
        app = self.app
        self.levels, self.counts = levels, counts
        self.has_terminal = any(b.source != "omarchy" for b in self.bindings)

        def draw():
            top = max(1, (app.height - 14) // 2)
            app.draw_ninja(top, (app.width - ninja.WIDTH) // 2, "ready", belt_rules.best(self.belts).name)
            app.center(top + 5, [("✦  BELT EXAM  ✦", app.accent | curses.A_BOLD)])
            y = top + 7
            for source, level in levels.items():
                belt = belt_rules.BELTS[level]
                app.center(y, [(f"{LABELS[source]:<8}", app.fg(curses.COLOR_CYAN) | curses.A_BOLD),
                               (f"  level {level} {LEVEL_NAMES[level - 1]}  ·  {counts[source]} moves  →  ", 0),
                               app.belt_bar(belt, 4), (f" {belt} belt", curses.A_BOLD)])
                y += 1
            app.center(y + 1, [("Every move once. Get them all right in under 3 s.", curses.A_DIM)])
            app.center(y + 2, [("Each right answer counts as learned, even if you fail.", curses.A_DIM)])
            app.center(app.height - 1, [("enter: start   q: back to the menu", curses.A_DIM)])
        app.draw = draw
        app.flush_input()
        while True:
            app.render()
            key = app.key()
            if key in BACK:
                return False
            if key in ENTER or key == " ":
                break
        app.draw = self.draw
        return True

    def frame_note(self):
        return f"question {self.asked}/{sum(self.counts.values())}"

    def question(self, binding, description, score, levels):
        self.asked += 1
        super().question(binding, description, score, levels)

    def right(self, seconds, limit, fast, score):
        super().right(seconds, limit, fast, score)
        if not fast:
            # Slow is not good enough in an exam
            app = self.app
            self.result = [(f"✗ {seconds:.1f} s", app.fg(curses.COLOR_RED) | curses.A_BOLD),
                           (f"  right, but over {limit:.0f} s", curses.A_DIM)]
            self.history[0] = (f"✗ {seconds:4.1f}  {self.description}", app.fg(curses.COLOR_RED))
            self.face = "sad"
            app.render()

    def exam_finish(self, results, levels):
        app = self.app
        self.check_belts()  # a passed exam shows the new belt first
        passed_all = all(passed for passed, _, _ in results.values())
        app.flush_input()

        def draw():
            top = max(1, (app.height - 12) // 2)
            app.draw_ninja(top, (app.width - ninja.WIDTH) // 2, "cheer" if passed_all else "calm",
                           belt_rules.best(self.belts).name)
            app.center(top + 5, [("Exam over", curses.A_BOLD)])
            y = top + 7
            for source, (passed, right, total) in results.items():
                verdict = ("passed", app.fg(curses.COLOR_GREEN) | curses.A_BOLD) if passed \
                    else ("not passed", app.fg(curses.COLOR_RED) | curses.A_BOLD)
                app.center(y, [(f"{LABELS[source]:<8}", app.fg(curses.COLOR_CYAN) | curses.A_BOLD),
                               (f"  level {levels[source]}  {right}/{total}  ", 0), verdict])
                y += 1
            if not passed_all:
                app.center(y + 1, [("The ones you got right now count as learned.", curses.A_DIM)])
            app.center(app.height - 1, [("any key: back to the menu", curses.A_DIM)])
        app.draw = draw
        app.render()
        app.key()


class Moves:
    """Every shortcut by source and level, with what you already learned."""

    def __init__(self, app):
        self.app = app
        self.by_source = quiz.moves_by_level(app.bindings)
        self.sources = list(self.by_source)
        self.source = app.source if app.source in self.sources else (self.sources or [None])[0]
        self.level = 1
        self.top = 0
        self.progress = {mode: prog.load(progress_path(mode)) for mode in ("quiz", "practice")}

    def items(self):
        return self.by_source.get(self.source, {}).get(self.level, [])

    def rows_shown(self):
        return max(1, self.app.height - 7)

    def show(self):
        app = self.app
        app.draw = self.draw
        while True:
            app.render()
            key = app.key()
            if key in BACK or key in ENTER:
                return
            last_top = max(0, len(self.items()) - self.rows_shown())
            if key in LEFT + RIGHT:
                self.level = (self.level - 1 + (1 if key in RIGHT else -1)) % LAST_LEVEL + 1
                self.top = 0
            elif key == "Tab" and self.sources:
                self.source = self.sources[(self.sources.index(self.source) + 1) % len(self.sources)]
                self.top = 0
            elif key in DOWN:
                self.top = min(last_top, self.top + 1)
            elif key in UP:
                self.top = max(0, self.top - 1)
            elif key == " ":
                self.top = min(last_top, self.top + self.rows_shown())

    def draw(self):
        app = self.app
        app.put(0, 2, "Moves", app.accent | curses.A_BOLD)
        x = 2
        for source in self.sources:
            on = source == self.source
            attr = (app.accent | curses.A_BOLD | curses.A_REVERSE) if on else curses.A_DIM
            x = app.put(2, x, f" {LABELS[source]} ", attr) + 1
        x = 2
        for level, name in enumerate(LEVEL_NAMES, start=1):
            count = len(self.by_source.get(self.source, {}).get(level, []))
            on = level == self.level
            attr = (app.fg(curses.COLOR_CYAN) | curses.A_BOLD) if on else curses.A_DIM
            x = app.put(3, x, f"{'▸' if on else ' '} {level} {name} ({count})", attr) + 2

        items = self.items()
        width = min(32, max((len(" or ".join(b.keys)) for b in items), default=0))
        app.put(5, 2, f"Q P  {'keys':<{width}}  action", curses.A_DIM)
        for i, b in enumerate(items[self.top:self.top + self.rows_shown()]):
            marks = [("✓" if prog.is_passed(self.progress[mode], b) else "·",
                      app.fg(curses.COLOR_GREEN) if prog.is_passed(self.progress[mode], b) else curses.A_DIM)
                     for mode in ("quiz", "practice")]
            combo = " or ".join(b.keys)
            if len(combo) > width:
                combo = combo[:width - 1] + "…"
            app.puts(6 + i, 2, [marks[0], (" ", 0), marks[1], ("  ", 0),
                                (f"{combo:<{width}}", app.fg(curses.COLOR_CYAN)), ("  ", 0),
                                (b.description, 0)])
        if len(items) > self.rows_shown():
            end = min(len(items), self.top + self.rows_shown())
            app.put(app.height - 1, app.width - 14, f"{self.top + 1}-{end}/{len(items)}", curses.A_DIM)
        app.puts(app.height - 1, 2, [("←→", app.accent), (" level   ", curses.A_DIM),
                                     ("tab", app.accent), (" source   ", curses.A_DIM),
                                     ("↑↓", app.accent), (" scroll   ", curses.A_DIM),
                                     ("q", app.accent), (" back   ", curses.A_DIM),
                                     ("✓ learned in Q quiz / P practice", curses.A_DIM)])
