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
    assert keys.fast_limit(["Space", "f", "f"]) > keys.fast_limit(["Ctrl + S"])


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
