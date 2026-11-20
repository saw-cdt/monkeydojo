"""Key sequences for practice mode. No I/O: only data in, data out.

A key string like "Ctrl + W d" is a sequence of tokens: ["Ctrl + W", "d"].
"""

QUIT = "Ctrl + C"

SPECIAL = {"Space", "Tab", "Enter", "Esc", "Backspace", "Up", "Down", "Left", "Right"}
ARROWS = {"Up", "Down", "Left", "Right"}
# Ctrl + these send a byte of their own. Ctrl + I/M/[ send the same as Tab/Enter/Esc.
CTRL_SYMBOLS = {"/", "\\", "]", "Space"}
CTRL_CLASHES = {"I", "M", "["}

# Time allowed for a right answer to count as fast (muscle memory, not recall)
FAST_BASE = 1.5
FAST_PER_KEY = 0.5


def split_keys(keys):
    """'Ctrl + W d' -> ['Ctrl + W', 'd']."""
    words = keys.split(" ")
    tokens, i = [], 0
    while i < len(words):
        token = words[i]
        while i + 2 < len(words) and words[i + 1] == "+":
            token += f" + {words[i + 2]}"
            i += 2
        tokens.append(token)
        i += 1
    return tokens


def can_type(token):
    """Whether a terminal can tell this key apart from the others."""
    if token == QUIT:
        return False
    *mods, key = token.split(" + ")
    single = len(key) == 1 and key.isprintable()
    if not mods:
        return single or key in SPECIAL
    if mods == ["Ctrl"]:
        letter = len(key) == 1 and "A" <= key <= "Z" and key not in CTRL_CLASHES
        return letter or key in CTRL_SYMBOLS or key in ARROWS
    if mods == ["Alt"]:
        return single or key in ARROWS
    if mods == ["Shift"]:
        return key == "Tab" or key in ARROWS
    return False


def targets(binding):
    """The binding's key sequences that can be typed in a terminal."""
    sequences = (split_keys(k) for k in binding.keys)
    return [s for s in sequences if all(can_type(t) for t in s)]


def check(typed, sequences):
    """'correct', 'partial' (keep typing) or 'wrong'."""
    if typed in sequences:
        return "correct"
    if any(s[:len(typed)] == typed for s in sequences):
        return "partial"
    return "wrong"


def fast_limit(sequence):
    return FAST_BASE + FAST_PER_KEY * len(sequence)
