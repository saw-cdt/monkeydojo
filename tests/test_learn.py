import random

from monkeydojo import learn, quiz
from monkeydojo import progress as prog
from monkeydojo.models import Binding

OMARCHY = [
    Binding("omarchy", "Focus on left window", ("SUPER + LEFT",)),
    Binding("omarchy", "Focus on right window", ("SUPER + RIGHT",)),
    Binding("omarchy", "Swap window to the left", ("SUPER SHIFT + LEFT",)),
    Binding("omarchy", "Swap window to the right", ("SUPER SHIFT + RIGHT",)),
    Binding("omarchy", "Next workspace", ("SUPER + TAB",)),
    Binding("omarchy", "Previous workspace", ("SUPER SHIFT + TAB",)),
    Binding("omarchy", "Switch to workspace <number>", ("SUPER + <number>",)),
    Binding("omarchy", "Move window to workspace <number>", ("SUPER SHIFT + <number>",)),
]
LAZYVIM = [
    Binding("lazyvim", "Lazygit (Root Dir)", ("Space g g",)),
    Binding("lazyvim", "Git Status", ("Space g s",)),
    Binding("lazyvim", "Lazy", ("Space l",)),
    Binding("lazyvim", "Notification History", ("Space n",)),
    Binding("lazyvim", "Go to Left Window", ("Ctrl + H",)),
    Binding("lazyvim", "Go to Right Window", ("Ctrl + L",)),
    Binding("lazyvim", "Prev Buffer", ("H", "[ b")),
]
ALL = OMARCHY + LAZYVIM


def test_new_bindings_come_a_few_at_a_time():
    progress = {}
    shown = []
    while (b := learn.next_new(OMARCHY, progress)):
        learn.introduce(progress, b)
        shown.append(b)
    assert shown == OMARCHY[:learn.NEW_AT_ONCE]
    # Training one of them opens the door for the next new one
    for _ in range(learn.TRAINED_BOX):
        prog.record_answer(progress, shown[0], True)
    assert learn.next_new(OMARCHY, progress) == OMARCHY[learn.NEW_AT_ONCE]


def test_only_introduced_bindings_are_asked():
    progress = {}
    learn.introduce(progress, OMARCHY[2])
    known = learn.known(OMARCHY, progress)
    assert known == [OMARCHY[2]]
    assert quiz.pick(known, progress, rng=random.Random(0)) == OMARCHY[2]


def test_old_progress_counts_as_introduced():
    progress = {OMARCHY[0].id: {"box": 4, "seen": 6, "correct": 5}}
    assert learn.introduced(progress, OMARCHY[0])
    assert not learn.introduced(progress, OMARCHY[1])


def test_family_hints():
    swap = learn.hints(OMARCHY[2], ALL)
    assert "SUPER SHIFT + arrows: Swap window to the right" in swap
    assert "SUPER + LEFT is Focus on left window" in swap
    assert learn.hints(OMARCHY[5], ALL) == ["SUPER + TAB is Next workspace"]
    assert learn.hints(LAZYVIM[0], ALL) == ["Space g … is a group: Git Status"]
    assert learn.hints(LAZYVIM[4], ALL) == ["Ctrl + hjkl: Go to Right Window"]
    # Space alone is not a family, and LazyVim H is not Ctrl + H's cousin
    assert learn.hints(LAZYVIM[2], ALL) == []
    assert all("Prev Buffer" not in h for h in learn.hints(LAZYVIM[4], ALL))


def test_meaning_of_what_was_pressed():
    assert learn.meaning(ALL, "omarchy", "SUPER + SHIFT + LEFT") == "Swap window to the left"
    assert learn.meaning(ALL, "omarchy", "SUPER + SHIFT + 4") == "Move window to workspace 4"
    assert learn.meaning(ALL, "omarchy", "SUPER + Q") is None
    assert learn.meaning(ALL, "lazyvim", ["Space", "g", "s"]) == "Git Status"
    assert learn.meaning(ALL, "lazyvim", ["Space", "g", "x"]) is None


def test_explain_a_wrong_quiz_choice():
    question = quiz.Question(OMARCHY[0], "keys_to_action", "SUPER + LEFT",
                             ("Focus on left window", "Next workspace"), 0)
    assert learn.explain_choice(ALL, question, 1) == "Next workspace is SUPER + TAB"
    question = quiz.Question(OMARCHY[0], "action_to_keys", "Focus on left window",
                             ("SUPER + LEFT", "SUPER SHIFT + LEFT"), 0)
    assert learn.explain_choice(ALL, question, 1) == "SUPER SHIFT + LEFT is Swap window to the left"
