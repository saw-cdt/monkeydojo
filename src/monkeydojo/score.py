"""Score of one session. No I/O."""

from dataclasses import dataclass, field


@dataclass
class Score:
    total: int = 0
    correct: int = 0
    fast: int = 0
    streak: int = 0
    best_streak: int = 0
    times: list[float] = field(default_factory=list)  # seconds of right answers

    def add(self, ok, fast=True, seconds=None):
        self.total += 1
        if not ok:
            self.streak = 0
            return
        self.correct += 1
        self.fast += bool(fast)
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        if seconds is not None:
            self.times.append(seconds)

    @property
    def percent(self):
        return self.correct * 100 // self.total if self.total else 0

    @property
    def average(self):
        """Average seconds of right answers, or None."""
        return sum(self.times) / len(self.times) if self.times else None
