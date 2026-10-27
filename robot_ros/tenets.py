"""Four tenets, 4-bit code: Cost, Bridge, Work, Theory (MSB->LSB).
Active-low: 0 = within limit (lit), 1 = over limit (dark). 0000 = online."""
from dataclasses import dataclass

ORDER = ("cost", "bridge", "work", "theory")

# Growing limits: level 0 is tight; each level loosens one step (bounded).
LEVELS = [
    {"cost": 1.0, "bridge": 3, "work": 10, "theory": 0},
    {"cost": 2.0, "bridge": 4, "work": 15, "theory": 0},
    {"cost": 5.0, "bridge": 5, "work": 25, "theory": 1},
    {"cost": 10.0, "bridge": 6, "work": 40, "theory": 1},
]
MAX_LEVEL = len(LEVELS) - 1


@dataclass
class Usage:
    cost: float = 0.0     # dollars
    bridge: int = 0       # hops
    work: int = 0         # steps (each retry adds work)
    theory: int = 0       # unverified claims


def limits_for(level: int) -> dict:
    return LEVELS[max(0, min(level, MAX_LEVEL))]


def code(usage: Usage, level: int = 0) -> str:
    lim = limits_for(level)
    return "".join("1" if getattr(usage, k) > lim[k] else "0" for k in ORDER)


def is_lit(c: str) -> bool:
    return c == "0000"


class TenetLevel:
    """Grows after N consecutive lit, high-scoring actions; tightens one step on dark."""

    def __init__(self, grow_after: int = 5, high_score: int = 8, level: int = 0):
        self.grow_after, self.high_score, self.level, self.streak = grow_after, high_score, level, 0

    def observe(self, lit: bool, score: float) -> int:
        if not lit:
            self.level = max(0, self.level - 1)
            self.streak = 0
        elif score >= self.high_score:
            self.streak += 1
            if self.streak >= self.grow_after:
                self.level = min(MAX_LEVEL, self.level + 1)
                self.streak = 0
        else:
            self.streak = 0
        return self.level
