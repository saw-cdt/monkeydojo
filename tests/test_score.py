from monkeydojo.score import Score
from monkeydojo.ui import terminal
from test_quiz import make_bindings


def test_streak_resets_on_a_mistake_and_keeps_the_best():
    s = Score()
    for ok in (True, True, True, False, True):
        s.add(ok, fast=True, seconds=1.0)
    assert (s.total, s.correct, s.streak, s.best_streak) == (5, 4, 1, 3)
    assert s.percent == 80


def test_average_only_counts_right_answers():
    s = Score()
    s.add(True, fast=True, seconds=1.0)
    s.add(True, fast=False, seconds=3.0)
    s.add(False)
    assert s.average == 2.0
    assert s.fast == 1


def test_empty_score():
    s = Score()
    assert s.percent == 0 and s.average is None


class FakeQuizView:
    """Answers right a fixed number of times, then quits."""

    def __init__(self, answers):
        self.answers = answers
        self.finished = None
        self.intros = 0

    def start(self, levels):
        pass

    def choose(self, question, score, levels):
        if not self.answers:
            return None
        right = self.answers.pop(0)
        return question.correct_index if right else (question.correct_index + 1) % 4

    def intro(self, binding, hints, levels):
        self.intros += 1
        return True

    def result(self, question, answer, score, mistake=None):
        pass

    def unlocked(self, source, level):
        pass

    def finish(self, score):
        self.finished = score


def test_quiz_loop_works_with_any_view():
    bindings = make_bindings()
    progress, saves = {}, []
    view = FakeQuizView([True, False, True])
    score = terminal.run(bindings, progress, saves.append, view)
    assert view.finished is score
    assert (score.total, score.correct) == (3, 2)
    assert len(saves) == 3 + view.intros
    assert view.intros >= 1  # new bindings are shown before they are asked
    assert sum(e["seen"] for e in progress.values()) == 3
