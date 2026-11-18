# Mon-Key Dojo

A terminal quiz to learn your [Omarchy](https://omarchy.org) keybindings.

Omarchy ships with 200+ keybindings. Looking them up is easy; remembering them is not.
Mon-Key Dojo reads the bindings from your own system and quizzes you on them, so it
always matches your setup, including any custom bindings you add.

The name is a pun: *mon* ("my"), *key*, and *monkey*.

## Requirements

- Omarchy
- Python 3.10+

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
What does SUPER + W do?
  1) Toggle nightlight
  2) Close window
  3) Next workspace
  4) Calculator
> 2
Correct!

What is the shortcut for Browser?
  1) SUPER + G
  2) SUPER SHIFT + RETURN
  3) SUPER + 3
  4) SUPER CTRL + D
>
```

Answer with `1`-`4`. Type `q` to quit and see your score.

### Levels

| Level | Name       | What it covers                                       |
|-------|------------|------------------------------------------------------|
| 1     | Essentials | Terminal, browser, windows, workspaces, focus        |
| 2     | Daily use  | Menus, clipboard, screen capture, scratchpad, groups |
| 3     | Advanced   | Everything else                                      |

You start at level 1. The next level unlocks when you have learned 80% of the
current one. Earlier levels keep showing up so you don't forget them.

### Spaced repetition

Every binding sits in a box from 0 to 5 (the
[Leitner system](https://en.wikipedia.org/wiki/Leitner_system)). A right answer
moves it up one box, a wrong answer sends it back to 0. Bindings in lower boxes
are asked more often. A binding counts as learned at box 3.

Progress is saved to `~/.local/share/monkeydojo/progress.json`.

### Options

```
--level N   practice only level N
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
├── sources/        # where bindings come from (one module per source)
│   └── omarchy.py
├── levels.py       # which binding belongs to which level
├── quiz.py         # question logic, no I/O
├── progress.py     # Leitner boxes and the progress file
└── ui/
    └── terminal.py # print/input interface
```

The core (`quiz.py`, `progress.py`, `levels.py`) never prints, reads input or
runs commands. Sources turn external data into `Binding` objects, and UIs show
questions to the user. Adding a new source or UI does not touch the core.

## Roadmap

- [x] Multiple-choice quiz from your Omarchy keybindings
- [x] Filter noisy bindings and add difficulty levels
- [x] Save progress and use spaced repetition
- [x] Package layout and tests
- [ ] LazyVim keybindings
- [ ] Interactive TUI
- [ ] Keybinding of the day (notification / Waybar module)
- [ ] Translations

## License

[MIT](LICENSE)
