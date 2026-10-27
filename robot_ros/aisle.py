"""First skill: aisle setting on a simulated store grid with movable racks."""
import random
from .tenets import Usage

W, H = 12, 8


def plan_layout(params):
    """Write the full plan before acting: list of rack placements."""
    gap, rows = params["aisle_width"], params["rack_rows"]
    plan, x = [], 1
    for _ in range(rows):
        if x >= W - 1:
            break
        plan.append({"move_rack_to_col": x, "rows": (1, H - 2)})
        x += 1 + gap
    return plan


def render(plan):
    g = [["." for _ in range(W)] for _ in range(H)]
    for step in plan:
        for y in range(step["rows"][0], step["rows"][1] + 1):
            g[y][step["move_rack_to_col"]] = "#"
    return "\n".join("".join(r) for r in g)


def score_layout(plan, job):
    """1-10: capacity vs job demand, aisle width vs cart width."""
    if not plan:
        return 1.0
    racks = len(plan)
    cols = [p["move_rack_to_col"] for p in plan]
    gaps = [b - a - 1 for a, b in zip(cols, cols[1:])] or [W]
    fit = 1.0 if min(gaps) >= job["cart_width"] else 0.3
    cap = min(1.0, racks / job["racks_needed"])
    waste = max(0, min(gaps) - job["cart_width"]) * 0.1
    return round(max(1.0, min(10.0, 10 * fit * cap - 10 * waste)), 1)


def make_attempt(job, seed=0):
    rng = random.Random(seed)

    def attempt(i, first):
        if i == 0 and first:
            params = dict(first)
        else:
            params = {"aisle_width": rng.randint(1, 3), "rack_rows": rng.randint(2, 6)}
        plan = plan_layout(params)
        usage = Usage(cost=0.1, bridge=1, work=len(plan), theory=0)
        return params, score_layout(plan, job), usage, plan
    return attempt
