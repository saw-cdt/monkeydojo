"""Quiz logic. No printing, no input, no files: only data in, data out."""

import random

from monkeydojo import progress as prog
from monkeydojo.levels import LAST_LEVEL, level_of
from monkeydojo.models import Question

UNLOCK_RATIO = 0.8


def level_stats(bindings, progress, level):
    """Return (learned, total) for a level."""
    items = [b for b in bindings if level_of(b) == level]
    learned = sum(1 for b in items if prog.is_learned(progress, b))
    return learned, len(items)


def unlocked_level(bindings, progress):
    """Highest level the user can practice."""
    for level in range(1, LAST_LEVEL):
        learned, total = level_stats(bindings, progress, level)
        if learned < UNLOCK_RATIO * total:
            return level
    return LAST_LEVEL


def build_pool(bindings, progress, forced_level=None):
    """Return (bindings to ask about, current level)."""
    if forced_level:
        return [b for b in bindings if level_of(b) == forced_level], forced_level
    level = unlocked_level(bindings, progress)
    # Include earlier levels so old bindings keep getting reviewed
    return [b for b in bindings if level_of(b) <= level], level


def pick(pool, progress, last=None, rng=random):
    """Weighted random pick: lower box = higher chance."""
    choices = [b for b in pool if b != last] or pool
    weights = [2 ** (prog.MAX_BOX - prog.box(progress, b)) for b in choices]
    return rng.choices(choices, weights)[0]


def make_question(bindings, binding, rng=random):
    if rng.random() < 0.5:
        # Keys -> action. Skip actions that share the key, so only one answer is right.
        kind = "keys_to_action"
        subject = rng.choice(binding.keys)
        others = sorted({b.description for b in bindings if subject not in b.keys})
        correct = binding.description
    else:
        kind = "action_to_keys"
        subject = binding.description
        all_keys = {k for b in bindings for k in b.keys}
        others = sorted(all_keys - set(binding.keys))
        correct = rng.choice(binding.keys)

    options = [correct] + rng.sample(others, 3)
    rng.shuffle(options)
    return Question(binding, kind, subject, tuple(options), options.index(correct))
