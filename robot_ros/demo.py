"""Pure-Python sim demo of the tenets of superintelligence: python -m robot_ros.demo"""
from .limiter import Limiter
from .brain import Brain
from .aisle import make_attempt, render


def run(jobs=8, threshold=7, grow_after=3, quiet=False):
    lim, brain = Limiter(threshold=threshold), Brain(grow_after=grow_after)
    job = {"name": "aisle-setting", "cart_width": 2, "racks_needed": 4}
    out = []
    if not quiet:
        print("tenets of superintelligence: Cost, Bridge, Work, Theory (0000 = online, all lit)")
    for n in range(jobs):
        res = lim.run(job["name"], make_attempt(job, seed=n), level=brain.tenet_level,
                      first_params=brain.suggest(job["name"]))
        ok = brain.observe(res)
        line = (f"job {n+1}: tries={res.tries} best={res.score} code={res.code} "
                f"{'lit -> brain' if ok else 'dark -> held'} tenet_level={brain.tenet_level} params={res.params}")
        out.append(line)
        if not quiet:
            print(line)
    best = brain.suggest(job["name"])
    if not quiet and best:
        from .aisle import plan_layout
        print("\n0000 layout built by brain memory:")
        print(render(plan_layout(best)))
    return brain, out


if __name__ == "__main__":
    run()
