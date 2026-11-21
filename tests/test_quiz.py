import random

from monkeydojo import progress as prog
from monkeydojo import quiz
from monkeydojo.levels import LEVELS
from monkeydojo.models import Binding


def make_bindings():
    level1 = sorted(LEVELS["omarchy"][0])
    bindings = [Binding("omarchy", d, (f"SUPER + K{i}",)) for i, d in enumerate(level1)]
    bindings.append(Binding("omarchy", "Apps menu", ("SUPER ALT + SPACE",)))  # level 2
    # Two actions sharing a key, like ALT + TAB in Omarchy
    bindings.append(Binding("omarchy", "Focus on next window", ("ALT + TAB",)))
    bindings.append(Binding("omarchy", "Reveal active window on top", ("ALT + TAB",)))
    bindings += [Binding("omarchy", f"Extra {i}", (f"SUPER CTRL + E{i}",)) for i in range(10)]
    return bindings


def learned(bindings, count):
    return {b.id: {"box": 3} for b in bindings[:count]}


def test_every_question_has_exactly_one_right_answer():
    bindings = make_bindings()
    rng = random.Random(42)
    for _ in range(5000):
        binding = rng.choice(bindings)
        q = quiz.make_question(bindings, binding, rng)
        assert len(set(q.options)) == 4
        if q.kind == "keys_to_action":
            right = [o for o in q.options if q.subject in next(b.keys for b in bindings if b.description == o)]
        else:
            right = [o for o in q.options if o in binding.keys]
        assert right == [q.options[q.correct_index]]


def test_level_2_unlocks_only_when_every_binding_is_learned():
    bindings = make_bindings()
    total = len(LEVELS["omarchy"][0])
    assert quiz.unlocked_level(bindings, learned(bindings, total - 1)) == 1
    assert quiz.unlocked_level(bindings, learned(bindings, total)) == 2


def test_a_mistake_on_an_old_binding_does_not_lock_the_level_again():
    bindings = make_bindings()
    total = len(LEVELS["omarchy"][0])
    progress = {}
    for b in bindings[:total]:
        for _ in range(prog.LEARNED_BOX):
            prog.record_answer(progress, b, True)
    assert quiz.unlocked_level(bindings, progress) == 2
    prog.record_answer(progress, bindings[0], False)
    assert quiz.unlocked_level(bindings, progress) == 2


def test_pool_includes_earlier_levels():
    bindings = make_bindings()
    total = len(LEVELS["omarchy"][0])
    pool, levels = quiz.build_pool(bindings, learned(bindings, total))
    assert levels == {"omarchy": 2}
    assert len(pool) == total + 1


def test_empty_level_is_skipped():
    bindings = [b for b in make_bindings() if b.description != "Apps menu"]
    total = len(LEVELS["omarchy"][0])
    assert quiz.unlocked_level(bindings, learned(bindings, total)) == 3


def test_pick_prefers_low_boxes():
    a = Binding("omarchy", "A", ("1",))
    b = Binding("omarchy", "B", ("2",))
    progress = {a.id: {"box": 5}}
    rng = random.Random(0)
    picks = [quiz.pick([a, b], progress, rng=rng) for _ in range(1000)]
    assert picks.count(b) > 900


def test_pick_avoids_repeating_last():
    a = Binding("omarchy", "A", ("1",))
    b = Binding("omarchy", "B", ("2",))
    assert all(quiz.pick([a, b], {}, last=a) == b for _ in range(50))


def test_sources_level_up_independently():
    omarchy = make_bindings()
    lazyvim = [Binding("lazyvim", f"Vim {i}", (f"Space {i}",)) for i in range(10)]
    total = len(LEVELS["omarchy"][0])
    _, levels = quiz.build_pool(omarchy + lazyvim, learned(omarchy, total))
    assert levels == {"omarchy": 2, "lazyvim": 3}  # lazyvim sample has no level 1 or 2


def test_wrong_options_come_from_same_source():
    omarchy = make_bindings()
    lazyvim = [Binding("lazyvim", f"Vim {i}", (f"Space {i}",)) for i in range(10)]
    bindings = omarchy + lazyvim
    rng = random.Random(1)
    for _ in range(500):
        q = quiz.make_question(bindings, rng.choice(lazyvim), rng)
        for option in q.options:
            assert option.startswith(("Vim", "Space"))
