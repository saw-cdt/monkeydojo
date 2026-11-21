"""Belts: the level of a source, shown like a martial arts rank. No I/O.

Levels 1, 2 and 3 are the white, yellow and green belts. Learning the last level
gives the red belt.
"""

import math
from dataclasses import dataclass

from monkeydojo import quiz
from monkeydojo.levels import LAST_LEVEL

BELTS = ("white", "yellow", "green", "red")
STRIPES = 5  # dots that fill up on the way to the next belt


@dataclass(frozen=True)
class Belt:
    index: int        # 0 white ... 3 red
    learned: int      # bindings learned in the current level
    needed: int       # learned bindings needed for the next belt (0 at the red belt)
    exam_ready: bool = False  # everything is learned, only the exam is left

    @property
    def name(self):
        return BELTS[self.index]

    @property
    def next_name(self):
        return BELTS[self.index + 1] if self.index + 1 < len(BELTS) else None

    @property
    def stripes(self):
        """How many of the STRIPES dots are lit."""
        if not self.needed:
            return STRIPES
        return min(STRIPES, STRIPES * self.learned // self.needed)


def belt(bindings, progress, exams=False):
    """Belt for the bindings of one source. With `exams`, a belt is won by its exam."""
    level = quiz.unlocked_level(bindings, progress, exams)
    learned, total = quiz.passed_stats(bindings, progress, level)
    needed = math.ceil(quiz.UNLOCK_RATIO * total)
    if level == LAST_LEVEL and quiz.level_done(bindings, progress, level, exams):
        return Belt(len(BELTS) - 1, learned, 0)
    return Belt(level - 1, learned, needed, exams and learned >= needed)


def belts(bindings, progress, exams=False):
    """{source: Belt} for every source in `bindings`."""
    return {source: belt(items, progress, exams) for source, items in quiz.by_source(bindings).items()}


def best(belts_by_source):
    """The highest belt, or the white one if there are none."""
    return max(belts_by_source.values(), key=lambda b: b.index, default=Belt(0, 0, 0))
