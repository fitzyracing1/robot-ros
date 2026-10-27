"""Brain: receives only lit actions, remembers best params per task, reads light.json (never writes)."""
import json, os
from types import MappingProxyType
from .tenets import TenetLevel

LIGHT_PATH = os.path.join(os.path.dirname(__file__), "light.json")


def load_light(path=LIGHT_PATH):
    with open(path) as f:
        return MappingProxyType(json.load(f))


class Brain:
    def __init__(self, grow_after: int = 5):
        self.light = load_light()
        self.memory = {}   # task -> (best score, params)
        self.log = []
        self.rejected = 0
        self.tenets = TenetLevel(grow_after=grow_after)

    @property
    def tenet_level(self):
        return self.tenets.level

    def observe(self, result):
        """Every gate outcome updates the tenet level; only lit ones are accepted."""
        self.tenets.observe(result.lit, result.score)
        return self.receive(result)

    def receive(self, result) -> bool:
        if not result.lit:
            self.rejected += 1
            return False
        self.log.append(result)
        prev = self.memory.get(result.task)
        if prev is None or result.score > prev[0]:
            self.memory[result.task] = (result.score, dict(result.params))
        return True

    def suggest(self, task):
        m = self.memory.get(task)
        return dict(m[1]) if m else None
