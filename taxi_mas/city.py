from __future__ import annotations
from dataclasses import dataclass
from .utils import Pos, manhattan, clamp
import random

@dataclass
class CityGrid:
    """Клеточный город width x height. 1 шаг = 1 такт."""
    width: int = 25
    height: int = 25

    def random_pos(self, rng: random.Random) -> Pos:
        return (rng.randrange(self.width), rng.randrange(self.height))

    def distance(self, a: Pos, b: Pos) -> int:
        return manhattan(a, b)

    def step_towards(self, a: Pos, target: Pos) -> Pos:
        ax, ay = a
        tx, ty = target

        if ax < tx:
            ax += 1
        elif ax > tx:
            ax -= 1
        elif ay < ty:
            ay += 1
        elif ay > ty:
            ay -= 1

        ax = clamp(ax, 0, self.width - 1)
        ay = clamp(ay, 0, self.height - 1)
        return (ax, ay)
