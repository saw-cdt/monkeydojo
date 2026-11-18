from monkeydojo.sources.omarchy import parse

SAMPLE = """\
SUPER + W                           → Close window
SUPER SHIFT + RETURN                → Browser
SUPER SHIFT + B                     → Browser
SUPER + 1                           → Switch to workspace 1
SUPER + 2                           → Switch to workspace 2
SUPER + 0                           → Switch to workspace 10
XF86AudioMute                       → Mute
SUPER + LEFT MOUSE BUTTON           → Move window
SUPER + mouse_down                  → Scroll active workspace forward
this line has no arrow
"""


def by_description(bindings):
    return {b.description: b for b in bindings}


def test_parses_simple_line():
    b = by_description(parse(SAMPLE))["Close window"]
    assert b.source == "omarchy"
    assert b.keys == ("SUPER + W",)


def test_groups_multiple_keys_for_same_action():
    assert by_description(parse(SAMPLE))["Browser"].keys == ("SUPER SHIFT + B", "SUPER SHIFT + RETURN")


def test_collapses_numbered_bindings():
    result = by_description(parse(SAMPLE))
    assert result["Switch to workspace <number>"].keys == ("SUPER + <number>",)
    assert not any("workspace 1" in d for d in result)


def test_filters_noise():
    result = by_description(parse(SAMPLE))
    assert "Mute" not in result
    assert "Move window" not in result
    assert "Scroll active workspace forward" not in result


def test_total_count():
    assert len(parse(SAMPLE)) == 3
