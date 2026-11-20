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
| Apps (Terminal, Browser, File manager, Editor) | the app opens, and only its new window is closed |

Wrong answers are still caught, so they never run anything. Actions that cannot
be undone safely (Close window, Lock system, copy/paste, ...) are still asked
but only check the shortcut. It uses the same progress as `--practice`.

Some effects depend on your layout: "Toggle window split" only works on dwindle
workspaces, and focus actions need another window in that direction.

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
├── real.py         # real mode: runs an action for a moment, then undoes it
├── sources/        # where bindings come from (one module per source)
│   ├── omarchy.py
│   ├── lazyvim.py       # runs nvim --headless with lazyvim_dump.lua
│   └── lazyvim_dump.lua
├── levels.py       # which binding belongs to which level
├── quiz.py         # question logic, no I/O
├── progress.py     # Leitner boxes and the progress file
└── ui/
    ├── terminal.py  # print/input interface
    ├── practice.py  # practice mode loop
    └── keyreader.py # reads raw keypresses from the terminal
```

The core (`quiz.py`, `progress.py`, `levels.py`, `keys.py`) never prints, reads input or
runs commands. Sources turn external data into `Binding` objects, and UIs show
questions to the user. Adding a new source or UI does not touch the core.

## Roadmap

- [x] Multiple-choice quiz from your Omarchy keybindings
- [x] Filter noisy bindings and add difficulty levels
- [x] Save progress and use spaced repetition
- [x] Package layout and tests
- [x] LazyVim keybindings
- [x] Practice mode: press the shortcut (LazyVim)
- [x] Practice mode for Omarchy (Hyprland submap)
- [x] Real mode: see the effect of a right answer
- [ ] Interactive TUI
- [ ] Keybinding of the day (notification / Waybar module)
- [ ] Translations

## License

[MIT](LICENSE)
