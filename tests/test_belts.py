from monkeydojo import belts
from monkeydojo import progress as prog
from monkeydojo.levels import LEVELS
from monkeydojo.models import Binding


def make_bindings():
    """10 bindings per level for one source."""
    out = []
    for level, descriptions in enumerate(LEVELS["omarchy"], start=1):
        out += [Binding("omarchy", d, (f"SUPER + K{level}{i}",)) for i, d in enumerate(sorted(descriptions)[:10])]
    out += [Binding("omarchy", f"Extra {i}", (f"SUPER CTRL + E{i}",)) for i in range(10)]  # level 3
    return out


def learn(bindings, level_items):
    return {b.id: {"box": prog.LEARNED_BOX} for b in level_items}


def test_new_user_has_a_white_belt_with_no_stripes():
    b = belts.belt(make_bindings(), {})
    assert (b.name, b.next_name, b.learned, b.needed, b.stripes) == ("white", "yellow", 0, 8, 0)


def test_stripes_fill_on_the_way_to_the_next_belt():
    bindings = make_bindings()
    b = belts.belt(bindings, learn(bindings, bindings[:4]))
    assert (b.learned, b.needed, b.stripes) == (4, 8, 2)


def test_each_level_is_a_belt_and_learning_the_last_one_is_red():
    bindings = make_bindings()
    level1, level2, level3 = bindings[:10], bindings[10:20], bindings[20:]
    assert belts.belt(bindings, learn(bindings, level1)).name == "yellow"
    assert belts.belt(bindings, learn(bindings, level1 + level2)).name == "green"
    red = belts.belt(bindings, learn(bindings, bindings))
    assert (red.name, red.next_name, red.needed, red.stripes) == ("red", None, 0, belts.STRIPES)


def test_best_belt_across_sources():
    bindings = make_bindings()
    by_source = {"omarchy": belts.belt(bindings, learn(bindings, bindings[:10])),
                 "lazyvim": belts.belt(bindings, {})}
    assert belts.best(by_source).name == "yellow"
    assert belts.best({}).name == "white"


def test_best_combo_is_kept_per_mode(tmp_path):
    path = tmp_path / "stats.json"
    stats = prog.load_stats(path)
    assert prog.record_combo(stats, "practice", 7)
    assert not prog.record_combo(stats, "practice", 5)
    assert prog.record_combo(stats, "quiz", 3)
    prog.save_stats(stats, path)
    assert prog.load_stats(path) == {"practice": {"best_combo": 7}, "quiz": {"best_combo": 3}}
