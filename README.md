# Mon-Key Dojo

A terminal quiz to learn your [Omarchy](https://omarchy.org) keybindings.

Omarchy ships with 200+ keybindings. Looking them up is easy; remembering them is not.
Mon-Key Dojo reads the bindings from your own system and quizzes you on them, so it
always matches your setup, including any custom bindings you add.

The name is a pun: *mon* ("my"), *key*, and *monkey*.

## Requirements

- Omarchy
- Python 3

No extra dependencies.

## Installation

```bash
git clone https://github.com/saw-cdt/monkeydojo.git
cd monkeydojo
./monkeydojo.py
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

## Roadmap

- [x] Multiple-choice quiz from your Omarchy keybindings
- [ ] Filter noisy bindings and add difficulty levels
- [ ] Save progress and use spaced repetition
- [ ] LazyVim keybindings
- [ ] Interactive TUI
- [ ] Keybinding of the day (notification / Waybar module)
- [ ] Translations

## License

[MIT](LICENSE)
