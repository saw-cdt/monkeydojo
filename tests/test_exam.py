from contextlib import contextmanager

from monkeydojo import belts, quiz
from monkeydojo import progress as prog
from monkeydojo.levels import LEVELS
from monkeydojo.models import Binding
from monkeydojo.ui import practice


def make_bindings():
    level1 = sorted(LEVELS["lazyvim"][0])[:4]
    level2 = sorted(LEVELS["lazyvim"][1])[:3]
    return [Binding("lazyvim", d, (f"Space {i}",)) for i, d in enumerate(level1 + level2)] + \
        [Binding("lazyvim", "Something advanced", ("Space z",))]


def learn_all(bindings, progress):
    for b in bindings:
        prog.learn_now(progress, b)


def test_with_exams_learning_a_level_is_not_enough():
    bindings = make_bindings()
    progress = {}
    learn_all(bindings[:4], progress)
    assert quiz.unlocked_level(bindings, progress) == 2           # quiz: learned is enough
    assert quiz.unlocked_level(bindings, progress, exams=True) == 1
    b = belts.belt(bindings, progress, exams=True)
    assert (b.name, b.exam_ready) == ("white", True)
    prog.pass_exam(progress, "lazyvim", 1)
    assert quiz.unlocked_level(bindings, progress, exams=True) == 2
    assert belts.belt(bindings, progress, exams=True).name == "yellow"


def test_the_exam_is_the_current_level_even_before_learning_it():
    bindings = make_bindings()
    plan = quiz.exam_plan(bindings, {})
    assert plan == {"lazyvim": (1, bindings[:4])}
    progress = {}
    for level in (1, 2, 3):
        prog.pass_exam(progress, "lazyvim", level)
    assert quiz.exam_plan(bindings, progress) == {}
    assert belts.belt(bindings, progress, exams=True).name == "red"


class FakeExamView:
    def __init__(self):
        self.results = None

    def exam_start(self, levels, counts):
        self.counts = counts

    def question(self, binding, description, score, levels):
        pass

    def right(self, seconds, limit, fast, score):
        pass

    def wrong(self, shown, score, mistake=None):
        pass

    def exam_finish(self, results, levels):
        self.results = results


def run_exam(monkeypatch, bindings, progress, wrong=(), slow=()):
    @contextmanager
    def keyboard(view, bindings, real_mode=False, block=()):
        yield None, None

    def prepare(view, trap, binding, rng, exclude=()):
        seconds = 5.0 if binding in slow else 1.0
        return binding.description, lambda: (binding not in wrong, seconds, None), [], 1, None

    monkeypatch.setattr(practice, "keyboard", keyboard)
    monkeypatch.setattr(practice, "prepare", prepare)
    monkeypatch.setattr(practice, "EXAM_PAUSE", 0)
    view = FakeExamView()
    return practice.exam(bindings, progress, lambda p: None, view), view


def test_passing_the_exam_skips_the_level_and_learns_it(monkeypatch):
    bindings = make_bindings()
    progress = {}
    results, view = run_exam(monkeypatch, bindings, progress)
    assert results == {"lazyvim": (True, 4, 4)}
    assert view.counts == {"lazyvim": 4}
    assert all(prog.is_learned(progress, b) for b in bindings[:4])
    assert quiz.unlocked_level(bindings, progress, exams=True) == 2


def test_one_mistake_or_slow_answer_fails_but_right_ones_count(monkeypatch):
    bindings = make_bindings()
    for wrong, slow in (([bindings[0]], ()), ((), [bindings[1]])):
        progress = {}
        results, _ = run_exam(monkeypatch, bindings, progress, wrong, slow)
        assert results == {"lazyvim": (False, 3, 4)}
        assert not prog.exam_passed(progress, "lazyvim", 1)
        assert sum(prog.is_learned(progress, b) for b in bindings[:4]) == 3
