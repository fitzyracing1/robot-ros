import json, os
from robot_ros.limiter import Limiter
from robot_ros.tenets import Usage, code, TenetLevel, MAX_LEVEL, limits_for
from robot_ros.brain import Brain, LIGHT_PATH
from robot_ros import demo


def seq(scores, usage=None):
    calls = []
    def attempt(i, first):
        calls.append(i)
        return {"i": i}, scores[i], usage or Usage(), ["step"]
    return attempt, calls


def test_pass_first_try():
    a, calls = seq([9, 1, 1])
    r = Limiter().run("t", a)
    assert r.tries == 1 and r.score == 9 and r.lit


def test_retry_cap_and_best_of():
    a, calls = seq([3, 6, 5, 10])
    r = Limiter().run("t", a)
    assert len(calls) == 3 and r.score == 6 and r.params == {"i": 1} and not r.lit


def test_cap_never_exceeds_three():
    assert Limiter(max_tries=10).max_tries == 3


def test_threshold_configurable():
    a, _ = seq([5, 5, 5])
    assert Limiter(threshold=5).run("t", a).tries == 1


def test_score_clamped():
    a, _ = seq([42])
    assert Limiter().run("t", a).score == 10


def test_tenets_code():
    assert code(Usage()) == "0000"
    assert code(Usage(cost=2)) == "1000"
    assert code(Usage(bridge=4)) == "0100"
    assert code(Usage(work=11)) == "0010"
    assert code(Usage(theory=1)) == "0001"
    assert code(Usage(cost=2, theory=1)) == "1001"


def test_retry_adds_work():
    a, _ = seq([1, 1, 1], Usage(work=3))
    r = Limiter().run("t", a)
    assert r.usage.work == 12 and r.code[2] == "1"


def test_no_plan_is_dark():
    r = Limiter().run("t", lambda i, f: ({}, 9, Usage(), []))
    assert not r.lit


def test_brain_only_lit():
    b = Brain()
    a, _ = seq([2, 2, 2]); assert not b.receive(Limiter().run("t", a))
    a, _ = seq([9]); assert b.receive(Limiter().run("t", a))
    assert len(b.log) == 1 and b.rejected == 1 and b.suggest("t") == {"i": 0}


def test_light_read_only():
    before = open(LIGHT_PATH).read()
    b = Brain()
    try:
        b.light["x"] = 1
        assert False
    except TypeError:
        pass
    assert open(LIGHT_PATH).read() == before and json.loads(before)["max_tries"] == 3


def test_tenet_level_grows_and_tightens():
    t = TenetLevel(grow_after=5)
    for _ in range(4): t.observe(True, 9)
    assert t.level == 0
    t.observe(True, 9); assert t.level == 1
    t.observe(False, 9); assert t.level == 0
    t.observe(False, 9); assert t.level == 0
    for _ in range(100): t.observe(True, 10)
    assert t.level == MAX_LEVEL
    assert limits_for(1)["cost"] > limits_for(0)["cost"]


def test_low_score_breaks_streak():
    t = TenetLevel(grow_after=2)
    t.observe(True, 9); t.observe(True, 7); t.observe(True, 9)
    assert t.level == 0


def test_looser_level_lights_code():
    u = Usage(cost=1.5)
    assert code(u, 0) == "1000" and code(u, 1) == "0000"


def test_aisle_demo():
    brain, out = demo.run(jobs=8, quiet=True)
    assert len(out) == 8 and brain.log
    assert all(r.lit and r.code == "0000" for r in brain.log)
    assert brain.suggest("aisle-setting")
    assert "tenet_level=" in out[-1]
