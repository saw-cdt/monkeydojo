# Mon-Key Dojo

A terminal quiz to learn your [Omarchy](https://omarchy.org) and
[LazyVim](https://www.lazyvim.org) keybindings.

Omarchy and LazyVim ship with hundreds of keybindings. Looking them up is easy;
remembering them is not. Mon-Key Dojo reads the bindings from your own system and
quizzes you on them, so it always matches your setup, including any custom
bindings you add.

The name is a pun: *mon* ("my"), *key*, and *monkey*.

## Requirements

- Python 3.10+
- Omarchy and/or Neovim with LazyVim (a source that is not installed is skipped)

No extra dependencies.

## Installation

With [pipx](https://pipx.pypa.io) (`sudo pacman -S python-pipx`):

```bash
git clone https://github.com/saw-cdt/monkeydojo.git
cd monkeydojo
pipx install .
monkeydojo
```

Or run it from the repo without installing:

```bash
PYTHONPATH=src python -m monkeydojo
```

## Usage

Run `monkeydojo` with no options to open the dojo:

```
                       M O N - K E Y   D O J O
     ▄▄▀▀▀▀▀▀▄▄█▀      ───────────────────────
   █▀█▀▄▄██▄▄▀█▀█      learn your keybindings by hand
   ▀█████▀▀█████▀
     ▀▀▀▀▀▀▀▀▀▀        Omarchy  ━━━━━━━━  white belt    ●●●○○ 11/16 to yellow
                       LazyVim  ━━━━━━━━  yellow belt   ●○○○○ 5/26 to green
                       best combo ×12  in practice

    ▸ Quiz      choose what a shortcut does
      Practice  press the shortcut
      Real      press it and see it happen
      Stats     your belts and boxes
```

Move with the arrows (or `j`/`k`), change Source and Level with `←`/`→` and start
with `Enter`. Leaving a session (`q`, `Ctrl + C`, or `Esc` on an Omarchy question)
takes you back to the menu.

During a session the Session panel shows your combo, score and average time, the
History panel your last answers, and the ninja monkey reacts to each answer. The
layout shrinks to fit small terminals, such as the dojo window in real mode.

The monkey takes its fur and face colors from your Omarchy theme
(`~/.local/state/omarchy/current/theme/colors.toml`), so it changes with the theme.

#### Belts

Each level is a belt: white (level 1), yellow (level 2) and green (level 3).
Learning the last level gives you the red belt. Every source has its own belt,
and the dots show how close you are to the next one. The monkey's headband is
the color of your belt. Quiz and practice have their own belts, because they
use separate progress. Real mode shares the practice progress, so it shows your
practice belt for Omarchy.

#### Combo

Every right answer in a row adds to your combo, and a mistake breaks it. The
monkey cheers every 5 in a row and when you beat your best combo. Quiz, practice
and real mode each keep their own best combo in `~/.local/share/monkeydojo/stats.json`.

The options below skip the menu and use the line by line interface. `--plain`
gives you that interface for the quiz.

### Quiz

Each question is multiple choice, in one of two directions:

```
[Omarchy] What does SUPER + W do?
  1) Toggle nightlight
  2) Close window
  3) Next workspace
  4) Calculator
> 2
Correct!

[LazyVim] What is the shortcut for Find Files (Root Dir)?
  1) Space b d
  2) Space Space
  3) g r
  4) Space s k
>
```

Answer with `1`-`4`. Type `q` to quit and see your score.

### Practice mode

A quiz trains you to *recognize* a shortcut. To build muscle memory you have to
*press* it. With `--practice` you see an action and press its shortcut:

```
[LazyVim] Find Files (Root Dir)
> Space f f  ✓ 1.1 s

[LazyVim] Save File
> Ctrl + S  ✓ 2.6 s, slow (aim for 2.0 s)

[LazyVim] Delete Buffer
> Space b b  ✗ It was: Space b d
  now press it: Space b d  ✓
```

Speed matters: a right answer only moves the binding up a box if it is fast
(1.5 s plus 0.5 s per key). After a mistake you press the right shortcut once
before moving on. Press `Ctrl + C` to quit.

Practice has its own progress (`~/.local/share/monkeydojo/practice.json`), so
`--practice --stats` and `--practice --reset` work on it separately.

#### Omarchy shortcuts

Omarchy shortcuts use SUPER, which Hyprland handles before the terminal sees it.
So during an Omarchy question Mon-Key Dojo switches Hyprland to a temporary
submap that catches your keys:

- the shortcut is recognized but **its real action never runs**, so you can
  practice "Close window" without closing anything
- workspace questions use a random number ("Switch to workspace 3")
- press `Esc` to quit

You always get your keyboard back: the submap is left after every question,
each question times out after 20 s, and if the program dies Hyprland leaves the
submap by itself within 30 s. The submap stays defined but unused until the next
config reload; it never touches your own bindings.

Omarchy practice needs a running Hyprland session. Without one, `--practice`
only uses LazyVim.

### Real mode

`--real` practices Omarchy shortcuts and, when you get one right, shows you the
real effect for a moment and then undoes it:

| Action | What you see |
|---|---|
| Workspaces, fullscreen, floating, focus, scratchpad, split | the action for 0.8 s, then it is undone |
| Menus (Omarchy, System, Keybindings, Apps, Theme, Emojis, Clipboard) | the menu opens for 1.5 s, then closes |
| Apps (Terminal, Browser, File manager, Editor) | the app opens floating, and only its new window is closed |

Wrong answers are still caught, so they never run anything. Actions that cannot
be undone safely (Close window, Lock system, copy/paste, ...) are still asked
but only check the shortcut. It uses the same progress as `--practice`.

#### The sandbox

So that window actions have something to act on, real mode starts on an empty
workspace (the highest free one from 10 down) with filler windows around the
dojo terminal:

```
┌──────┬──────┐
│ dojo │  A   │
├──────┼──────┤
│  B   │  C   │
└──────┴──────┘
```

After each effect the grid is checked and rebuilt if an action left it broken.
When you quit, only the filler windows are closed and the dojo terminal goes
back to the workspace you started on. If the dojo dies, the filler windows close
by themselves. If no workspace is free, real mode runs where you are.

The actions that have no effect yet, and how each one could be added, are
listed in [docs/real-mode.md](docs/real-mode.md).

### Levels

| Level | Name       | What it covers                                       |
|-------|------------|------------------------------------------------------|
| 1     | Essentials | Terminal, browser, windows, workspaces, focus        |
| 2     | Daily use  | Menus, clipboard, screen capture, scratchpad, groups |
| 3     | Advanced   | Everything else                                      |

You start at level 1. The next level unlocks when you have learned 80% of the
current one. Omarchy and LazyVim level up independently. Earlier levels keep showing up so you don't forget them.

### Spaced repetition

Every binding sits in a box from 0 to 5 (the
[Leitner system](https://en.wikipedia.org/wiki/Leitner_system)). A right answer
moves it up one box, a wrong answer sends it back to 0. Bindings in lower boxes
are asked more often. A binding counts as learned at box 3.

Progress is saved to `~/.local/share/monkeydojo/progress.json`.

### Options

```
--source S  practice only one source: omarchy or lazyvim
--level N   practice only level N
--practice  press the shortcut instead of choosing it
--real      Omarchy practice that shows the real effect of a right answer
--plain     line by line quiz instead of the menu
--stats     show your progress
--reset     delete your progress
```

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

### Project layout

```
src/monkeydojo/
├── cli.py          # argument parsing, wires everything together
├── models.py       # Binding and Question data classes
├── keys.py         # key sequences for practice mode, no I/O
├── hyprland.py     # catches Omarchy shortcuts with a Hyprland submap
├── real.py         # real mode: effects, undo and the sandbox workspace
├── sandbox_window.py # a filler window for the sandbox (one big letter)
├── sources/        # where bindings come from (one module per source)
│   ├── omarchy.py
│   ├── lazyvim.py       # runs nvim --headless with lazyvim_dump.lua
│   └── lazyvim_dump.lua
├── levels.py       # which binding belongs to which level
├── quiz.py         # question logic, no I/O
├── progress.py     # Leitner boxes, the progress file and the best combos
├── belts.py        # which belt a source is at, from its levels
├── score.py        # score of one session (combo, average time)
└── ui/
    ├── tui.py       # full screen interface (curses): menu, sessions, stats
    ├── ninja.py     # the ninja monkey sprite and its faces
    ├── theme.py     # the monkey's colors from the Omarchy theme
    ├── terminal.py  # quiz loop and its line by line view
    ├── practice.py  # practice mode loop and its line by line view
    └── keyreader.py # reads raw keypresses from the terminal
```

The core (`quiz.py`, `progress.py`, `levels.py`, `keys.py`, `score.py`, `belts.py`) never prints, reads input or
runs commands. Sources turn external data into `Binding` objects, and UIs show
questions to the user. The quiz and practice loops take a *view* object that
does all the showing, so the line by line interface and the TUI share the same
loop. Adding a new source or UI does not touch the core.

## Roadmap

- [x] Multiple-choice quiz from your Omarchy keybindings
- [x] Filter noisy bindings and add difficulty levels
- [x] Save progress and use spaced repetition
- [x] Package layout and tests
- [x] LazyVim keybindings
- [x] Practice mode: press the shortcut (LazyVim)
- [x] Practice mode for Omarchy (Hyprland submap)
- [x] Real mode: see the effect of a right answer
- [x] Interactive TUI
- [ ] Keybinding of the day (notification / Waybar module)
- [ ] Translations

## License

[MIT](LICENSE)
