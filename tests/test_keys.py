from monkeydojo import keys
from monkeydojo.models import Binding
from monkeydojo.ui.keyreader import decode


def test_split_keys():
    assert keys.split_keys("Space f f") == ["Space", "f", "f"]
    assert keys.split_keys("Ctrl + W d") == ["Ctrl + W", "d"]
    assert keys.split_keys("Ctrl + W Ctrl + D") == ["Ctrl + W", "Ctrl + D"]
    assert keys.split_keys("Space +") == ["Space", "+"]


def test_can_type():
    for token in ("f", "Space", "Esc", "Ctrl + S", "Ctrl + /", "Alt + j", "Ctrl + Up", "Shift + Tab"):
        assert keys.can_type(token), token
    for token in ("Ctrl + C", "Ctrl + I", "Ctrl + Shift + K", "F5", "Ctrl + s"):
        assert not keys.can_type(token), token


def test_targets_skip_untypable_keys():
    b = Binding("lazyvim", "X", ("Ctrl + Shift + K", "Space x"))
    assert keys.targets(b) == [["Space", "x"]]


def test_check():
    sequences = [["Space", "f", "f"], ["Space", "Space"]]
    assert keys.check(["Space"], sequences) == "partial"
    assert keys.check(["Space", "f"], sequences) == "partial"
    assert keys.check(["Space", "f", "f"], sequences) == "correct"
    assert keys.check(["Space", "Space"], sequences) == "correct"
    assert keys.check(["Space", "g"], sequences) == "wrong"
    assert keys.check(["g"], sequences) == "wrong"


def test_fast_limit_grows_with_length():
    assert keys.fast_limit(3) > keys.fast_limit(1)


def test_decode_plain_and_control():
    assert decode(b" ff") == ["Space", "f", "f"]
    assert decode(b"\x13") == ["Ctrl + S"]
    assert decode(b"\x1f") == ["Ctrl + /"]
    assert decode(b"\x00") == ["Ctrl + Space"]
    assert decode(b"\t\r\x7f") == ["Tab", "Enter", "Backspace"]
    assert decode(b"G") == ["G"]


def test_decode_escape_sequences():
    assert decode(b"\x1b") == ["Esc"]
    assert decode(b"\x1bj") == ["Alt + j"]
    assert decode(b"\x1b[A") == ["Up"]
    assert decode(b"\x1bOB") == ["Down"]
    assert decode(b"\x1b[1;5C") == ["Ctrl + Right"]
    assert decode(b"\x1b[Z") == ["Shift + Tab"]
    assert decode(b"\x1b[15~") == ["?"]


def test_decoded_names_match_source_names():
    # What the reader produces must equal what keys.split_keys produces
    from monkeydojo.sources.lazyvim import format_keys
    assert decode(b"\x17d") == keys.split_keys(format_keys("<C-W>d"))
    assert decode(b"\x1bn") == keys.split_keys(format_keys("<a-n>"))
    assert decode(b"\x1b[1;5A") == keys.split_keys(format_keys("<C-Up>"))


def test_instantiate_fills_in_number():
    import random
    b = Binding("omarchy", "Switch to workspace <number>", ("SUPER + <number>",))
    description, answers, n = keys.instantiate(b, random.Random(0))
    assert 1 <= n <= 9
    assert description == f"Switch to workspace {n}"
    assert answers == (f"SUPER + {n}",)
    plain = Binding("omarchy", "Close window", ("SUPER + W",))
    assert keys.instantiate(plain, random.Random(0)) == ("Close window", ("SUPER + W",), None)


def test_instantiate_can_skip_a_number():
    import random
    b = Binding("omarchy", "Switch to workspace <number>", ("SUPER + <number>",))
    rng = random.Random(0)
    assert all(keys.instantiate(b, rng, exclude={2})[2] != 2 for _ in range(200))


def test_real_actions_exist_in_levels():
    # Every real-mode action must be a description Omarchy really uses
    from monkeydojo.levels import LEVELS
    from monkeydojo.real import ACTIONS
    known = set().union(*LEVELS["omarchy"])
    assert set(ACTIONS) <= known


def test_hyprland_targets_skip_quit_key():
    assert keys.hyprland_targets(("ESCAPE", "SUPER + ESCAPE")) == ["SUPER + ESCAPE"]


def test_to_bind_keys():
    from monkeydojo.hyprland import to_bind_keys
    assert to_bind_keys("SUPER SHIFT + RETURN") == "SUPER + SHIFT + RETURN"
    assert to_bind_keys("SUPER + W") == "SUPER + W"
    assert to_bind_keys("F9") == "F9"
    assert to_bind_keys("SHIFT CTRL ALT + TAB") == "SHIFT + CTRL + ALT + TAB"


def test_judge_hyprland_events():
    from monkeydojo.hyprland import judge
    wanted = {7}
    assert judge(["mod", "wrong"], wanted) is None                 # SUPER alone
    assert judge(["wrong", "mod"], wanted) is None                 # either order
    assert judge(["key 7", "wrong"], wanted) == ("ok", 7)          # right shortcut + catchall
    assert judge(["key 3", "wrong"], wanted) == ("wrong", 3)       # another Omarchy shortcut
    assert judge(["wrong"], wanted) == ("wrong", None)             # any other key
    assert judge(["mod", "wrong", "wrong"], wanted) == ("wrong", None)  # SUPER then E, very fast
    assert judge(["quit", "wrong"], wanted) == ("quit", None)


def test_omarchy_combos_fill_in_numbers():
    from monkeydojo.ui.practice import omarchy_combos
    bindings = [
        Binding("omarchy", "Switch to workspace <number>", ("SUPER + <number>",)),
        Binding("omarchy", "Browser", ("SUPER SHIFT + RETURN",)),
        Binding("lazyvim", "Save File", ("Ctrl + S",)),
    ]
    combos = omarchy_combos(bindings)
    assert "SUPER + 0" in combos and "SUPER + 9" in combos
    assert "SUPER + SHIFT + RETURN" in combos
    assert len(combos) == 11
