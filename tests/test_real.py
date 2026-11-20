from monkeydojo import real
from monkeydojo.models import Binding


def test_actions_without_an_effect_still_pause(monkeypatch):
    slept = []
    monkeypatch.setattr(real.time, "sleep", slept.append)
    real.show(Binding("omarchy", "Screenshot", ("PRINT",)))
    assert slept == [real.NO_EFFECT_PAUSE]
