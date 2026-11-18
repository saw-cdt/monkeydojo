import json

from monkeydojo import progress as prog
from monkeydojo.models import Binding

TERMINAL = Binding("omarchy", "Terminal", ("SUPER + RETURN",))


def test_right_answer_moves_up_one_box():
    progress = {}
    prog.record_answer(progress, TERMINAL, True)
    prog.record_answer(progress, TERMINAL, True)
    assert prog.box(progress, TERMINAL) == 2


def test_wrong_answer_goes_back_to_zero():
    progress = {TERMINAL.id: {"box": 4, "seen": 4, "correct": 4}}
    prog.record_answer(progress, TERMINAL, False)
    assert prog.box(progress, TERMINAL) == 0
    assert progress[TERMINAL.id]["seen"] == 5


def test_box_never_goes_above_max():
    progress = {}
    for _ in range(prog.MAX_BOX + 3):
        prog.record_answer(progress, TERMINAL, True)
    assert prog.box(progress, TERMINAL) == prog.MAX_BOX


def test_save_and_load(tmp_path):
    path = tmp_path / "progress.json"
    progress = {}
    prog.record_answer(progress, TERMINAL, True)
    prog.save(progress, path)
    assert prog.load(path) == progress


def test_load_missing_file(tmp_path):
    assert prog.load(tmp_path / "nope.json") == {}


def test_migrates_version_1(tmp_path):
    path = tmp_path / "progress.json"
    path.write_text(json.dumps({"Terminal": {"box": 3, "seen": 3, "correct": 3}}))
    assert prog.box(prog.load(path), TERMINAL) == 3
