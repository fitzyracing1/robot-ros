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


from robot_ros.gravity import simulate, analyze, G


def test_gravity_level_at_rest():
    g = analyze(simulate(0))
    assert abs(sum(v * v for v in g["accel"]) ** 0.5 - G) < 1e-6
    assert g["tilt_deg"] == 0 and g["is_level"] and g["load_g"] == 1.0


def test_gravity_tilt_and_load():
    g = analyze(simulate(15, payload_kg=5))
    assert abs(g["tilt_deg"] - 15) < 0.01 and not g["is_level"] and abs(g["load_kg_est"] - 5) < 0.2
    assert analyze(simulate(15), max_tilt_deg=20)["is_level"]


def test_excess_tilt_is_dark_and_retries():
    a, calls = seq([9, 9, 9])
    r = Limiter().run("t", a, accel=simulate(12))
    assert len(calls) == 3 and r.score < 7 and not r.lit and not r.level_lit


def test_level_tilt_passes():
    a, calls = seq([9, 1, 1])
    r = Limiter().run("t", a, accel=simulate(5, noise=0.02))
    assert r.tries == 1 and r.lit and r.gravity["is_level"]


# --- real accelerometer wiring ---
from robot_ros.gravity import from_vector, offset_from_samples, to_ms2
from robot_ros.imu_source import ImuSource
from robot_ros.mpu6050 import raw_to_ms2


def test_vector_tilt_real_style_samples():
    # level board, slight bias like a cheap MPU-6050
    g = from_vector((0.12, -0.08, 9.79))
    assert g["tilt_deg"] < 1.0 and g["is_level"] and abs(g["load_g"] - 1) < 0.01
    # tipped ~20 deg about y: ax = -g sin20, az = g cos20
    g = from_vector((-3.355, 0.02, 9.218))
    assert abs(g["tilt_deg"] - 20) < 0.2 and not g["is_level"]
    # same reading reported in g units
    assert abs(from_vector((0.0, 0.0, 1.0), units="g")["load_g"] - 1) < 1e-6
    assert to_ms2((1, 0, 0), "g")[0] == G


def test_calibration_offset():
    samples = [(0.30, -0.20, 9.95), (0.32, -0.18, 9.97), (0.28, -0.22, 9.93)]
    off = offset_from_samples(samples)
    g = from_vector((0.30, -0.20, 9.95), offset=off)
    assert g["tilt_deg"] < 0.01 and abs(g["load_g"] - 1) < 1e-3


def test_mpu6050_raw_conversion():
    assert raw_to_ms2(bytes([0, 0, 0, 0, 0x40, 0]))[2] == G      # +16384 = 1 g
    assert raw_to_ms2(bytes([0xC0, 0, 0, 0, 0, 0]))[0] == -G     # -16384


def test_imu_detected_then_stale_is_dark():
    logs = []
    s = ImuSource("auto", detect_timeout_s=3, stale_ms=500, log=logs.append)
    s.on_imu(0.0, 0.0, 9.81, now=0.5)
    a, ok, mode = s.read(now=0.7)
    assert ok and mode == "imu" and a[2] == 9.81 and "real IMU" in logs[0]
    a, ok, mode = s.read(now=1.2)  # 700 ms since last message
    assert not ok and a is None and mode == "imu"
    r = Limiter().run("t", seq([9, 9, 9])[0], accel=a, sensor_ok=ok)
    assert not r.lit and not r.level_lit


def test_imu_required_never_arrives_is_dark():
    a, ok, mode = ImuSource("imu", log=lambda m: None).read(now=10)
    assert not ok and mode == "imu"


def test_fallback_to_sim_logged():
    logs = []
    s = ImuSource("auto", detect_timeout_s=3, log=logs.append)
    assert s.read(now=1)[1] is False                   # still waiting for IMU
    a, ok, mode = s.read(now=3.1)
    assert ok and mode == "sim" and "FALLING BACK TO SIM" in logs[0]
    assert Limiter().run("t", seq([9, 1, 1])[0], accel=a, sensor_ok=ok).lit
    assert ImuSource("sim").read(now=0)[2] == "sim"
