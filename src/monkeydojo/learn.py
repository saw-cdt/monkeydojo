"""Help to learn a binding, not only to be tested on it. No I/O.

- New bindings are shown before they are asked, a few at a time.
- Hints point at the family a shortcut belongs to (same keys with another modifier,
  the arrows, a LazyVim key group), so you learn the rule instead of every key.
- A wrong answer also tells what the answer you gave really does.
"""

from monkeydojo import keys
from monkeydojo import progress as prog

# How many bindings can be in training at once before a new one is shown
NEW_AT_ONCE = 3
# A binding stops being "in training" at this box
TRAINED_BOX = 2
HINT_NAMES = 3  # descriptions listed in a family hint, the rest is "…"
VIM_DIRECTIONS = {"H", "J", "K", "L"}


def introduced(progress, binding):
    """Whether the binding was already shown or asked."""
    return binding.id in progress


def introduce(progress, binding):
    progress.setdefault(binding.id, {"box": 0, "seen": 0, "correct": 0})


def next_new(pool, progress):
    """The binding to show next, or None if it is time to ask.

    Bindings come in pool order (earlier levels first), and only while fewer than
    NEW_AT_ONCE of the ones already shown are still in training.
    """
    new = [b for b in pool if not introduced(progress, b)]
    if not new:
        return None
    training = [b for b in pool if introduced(progress, b) and prog.box(progress, b) < TRAINED_BOX]
    return new[0] if len(training) < NEW_AT_ONCE else None


def known(pool, progress):
    """The bindings that can be asked: the ones already shown."""
    return [b for b in pool if introduced(progress, b)]


# --- family hints ------------------------------------------------------------

def _chord(token):
    """'SUPER SHIFT + LEFT' -> ({'SUPER', 'SHIFT'}, 'LEFT'); 'Ctrl + K' -> ({'CTRL'}, 'K')."""
    mods, _, key = token.rpartition(" + ")
    return frozenset(m.upper() for m in mods.split()), key


def _names(bindings):
    names = [b.description for b in bindings]
    more = "…" if len(names) > HINT_NAMES else ""
    return ", ".join(names[:HINT_NAMES]) + more


def _tokens(binding, k):
    # An Omarchy shortcut is one chord, even with spaces between the modifiers
    return [k] if binding.source == "omarchy" else keys.split_keys(k)


def _direction(source, key):
    """'arrows', 'hjkl' or None. Only LazyVim uses H J K L as directions."""
    if key.capitalize() in keys.ARROWS:
        return "arrows"
    if source != "omarchy" and key.upper() in VIM_DIRECTIONS:
        return "hjkl"
    return None


def hints(binding, bindings):
    """Short lines that link the binding to the ones that look like it.

    Pass the bindings being practiced, so hints only name ones you can meet.
    """
    others = [b for b in bindings if b.source == binding.source and b != binding]
    chords = [(b, o, *_chord(o)) for b in others for o in b.keys if len(_tokens(b, o)) == 1]
    lines = []
    for k in binding.keys:
        tokens = _tokens(binding, k)
        if len(tokens) > 1:
            # A key group: every LazyVim binding that starts the same way
            prefix = tokens[:-1]
            if prefix == ["Space"]:
                continue  # that is almost every binding, not a family
            group = [b for b in others if any(_tokens(b, o)[:-1] == prefix for o in b.keys)]
            if group:
                lines.append(f"{' '.join(prefix)} … is a group: {_names(group)}")
            continue
        mods, key = _chord(tokens[0])
        if not mods:
            continue
        if direction := _direction(binding.source, key):
            group = list(dict.fromkeys(b for b, _, m, o in chords
                                       if m == mods and _direction(b.source, o) == direction))
            if group:
                lines.append(f"{k.rpartition(' + ')[0]} + {direction}: {_names(group)}")
        if binding.source == "omarchy":
            # Same key with other modifiers, closest first: SUPER + TAB vs SUPER SHIFT + TAB
            cousins = sorted((len(mods ^ m), combo, b.description)
                             for b, combo, m, o in chords if o == key and m != mods)
            lines += [f"{combo} is {description}" for _, combo, description in cousins[:2]]
    return list(dict.fromkeys(lines))[:3]


# --- what a wrong answer does ------------------------------------------------

def _bind(combo):
    """'SUPER SHIFT + LEFT' and 'SUPER + SHIFT + LEFT' -> 'SUPER + SHIFT + LEFT'."""
    return " + ".join(w for w in combo.split() if w != "+")


def meaning(bindings, source, pressed):
    """The description of the binding with these keys, or None.

    `pressed` is a key string ('Space g g'), a list of tokens, or an Omarchy
    combo in hl.bind format ('SUPER + SHIFT + LEFT').
    """
    if source == "omarchy":
        wanted = _bind(pressed)
        for b in bindings:
            if b.source != source:
                continue
            for k in b.keys:
                if _bind(k) == wanted:
                    return b.description
                if keys.NUMBER in k:
                    for d in "0123456789":
                        if _bind(k.replace(keys.NUMBER, d)) == wanted:
                            return b.description.replace(keys.NUMBER, d)
        return None
    tokens = keys.split_keys(pressed) if isinstance(pressed, str) else list(pressed)
    for b in bindings:
        if b.source == source and any(keys.split_keys(k) == tokens for k in b.keys):
            return b.description
    return None


def explain_choice(bindings, question, answer):
    """What the wrong option of a quiz question really is, or None."""
    chosen = question.options[answer]
    source = question.binding.source
    if question.kind == "keys_to_action":
        for b in bindings:
            if b.source == source and b.description == chosen:
                return f"{chosen} is {' or '.join(b.keys)}"
        return None
    description = meaning(bindings, source, chosen)
    return f"{chosen} is {description}" if description else None
