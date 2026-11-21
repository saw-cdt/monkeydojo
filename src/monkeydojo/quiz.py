"""Quiz logic. No printing, no input, no files: only data in, data out."""

import random

from monkeydojo import progress as prog
from monkeydojo.levels import LAST_LEVEL, level_of
from monkeydojo.models import Question

# Every binding of a level has to be learned before the next one opens
UNLOCK_RATIO = 1.0


def by_source(bindings):
    grouped = {}
    for b in bindings:
        grouped.setdefault(b.source, []).append(b)
    return grouped


def level_stats(bindings, progress, level):
    """Return (learned, total) for a level."""
    items = [b for b in bindings if level_of(b) == level]
    learned = sum(1 for b in items if prog.is_learned(progress, b))
    return learned, len(items)


def passed_stats(bindings, progress, level):
    """Return (passed, total) for a level. Passed bindings stay passed after a mistake."""
    items = [b for b in bindings if level_of(b) == level]
    passed = sum(1 for b in items if prog.is_passed(progress, b))
    return passed, len(items)


def unlocked_level(bindings, progress):
    """Highest level the user can practice. Pass bindings from a single source."""
    for level in range(1, LAST_LEVEL):
        passed, total = passed_stats(bindings, progress, level)
        if passed < UNLOCK_RATIO * total:
            return level
    return LAST_LEVEL


def build_pool(bindings, progress, forced_level=None):
    """Return (bindings to ask about, {source: current level}).

    Each source levels up on its own.
    """
    pool, levels = [], {}
    for source, items in by_source(bindings).items():
        if forced_level:
            level = forced_level
            pool += [b for b in items if level_of(b) == level]
        else:
            level = unlocked_level(items, progress)
            # Include earlier levels so old bindings keep getting reviewed
            pool += [b for b in items if level_of(b) <= level]
        levels[source] = level
    return pool, levels


def pick(pool, progress, last=None, rng=random):
    """Weighted random pick: lower box = higher chance."""
    choices = [b for b in pool if b != last] or pool
    weights = [2 ** (prog.MAX_BOX - prog.box(progress, b)) for b in choices]
    return rng.choices(choices, weights)[0]


def make_question(bindings, binding, rng=random):
    # Wrong options come from the same source, otherwise they are too easy to spot
    same_source = [b for b in bindings if b.source == binding.source]

    if rng.random() < 0.5:
        # Keys -> action. Skip actions that share the key, so only one answer is right.
        kind = "keys_to_action"
        subject = rng.choice(binding.keys)
        others = sorted({b.description for b in same_source if subject not in b.keys})
        correct = binding.description
    else:
        kind = "action_to_keys"
        subject = binding.description
        all_keys = {k for b in same_source for k in b.keys}
        others = sorted(all_keys - set(binding.keys))
        correct = rng.choice(binding.keys)

    options = [correct] + rng.sample(others, min(3, len(others)))
    rng.shuffle(options)
    return Question(binding, kind, subject, tuple(options), options.index(correct))
