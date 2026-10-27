"""The limiter (gate): self-score 1-10, retry below threshold, up to 3 tries, keep best."""
from dataclasses import dataclass, field
from .tenets import Usage, code, is_lit


@dataclass
class Result:
    task: str
    params: dict
    score: float
    tries: int
    usage: Usage
    code: str
    plan: list = field(default_factory=list)
    plan_lit: bool = True
    gravity: dict = None
    level_lit: bool = True

    @property
    def lit(self) -> bool:
        return self.plan_lit and self.level_lit and is_lit(self.code)


class Limiter:
    def __init__(self, threshold: float = 7, max_tries: int = 3, work_per_try: int = 1,
                 max_tilt_deg: float = 10.0):
        self.max_tilt_deg = max_tilt_deg
        self.threshold, self.max_tries, self.work_per_try = threshold, min(max_tries, 3), work_per_try

    def run(self, task, attempt, level: int = 0, first_params=None, accel=None,
            sensor_ok=True):
        """attempt(try_index, first_params) -> (params, score, Usage, plan).
        accel: optional accelerometer (ax, ay, az); tilt over max_tilt_deg is a dark
        self-check: the score is capped below threshold, so the limiter retries.
        sensor_ok=False (stale or missing IMU data) is also a dark self-check."""
        from .gravity import analyze
        grav = analyze(accel, self.max_tilt_deg) if accel is not None else None
        best, total = None, Usage()
        tries = 0
        for i in range(self.max_tries):
            tries += 1
            params, score, u, plan = attempt(i, first_params)
            score = max(1.0, min(10.0, float(score)))
            if not sensor_ok or (grav and not grav["is_level"]):
                score = max(1.0, min(score, self.threshold - 1))
            total.cost += u.cost
            total.bridge = max(total.bridge, u.bridge)
            total.work += u.work + self.work_per_try  # each retry adds to Work
            total.theory += u.theory
            if best is None or score > best[1]:
                best = (params, score, plan)
            if score >= self.threshold:
                break
        params, score, plan = best
        plan_lit = bool(plan)  # Code rule: a written plan is required
        c = code(total, level)
        if score < self.threshold:
            c = c[:2] + "1" + c[3:] if c[2] == "0" else c  # work spent without passing -> Work dark
        return Result(task, params, score, tries, total, c, plan, plan_lit, grav,
                      sensor_ok and (grav is None or grav["is_level"]))
