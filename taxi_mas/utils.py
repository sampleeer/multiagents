from __future__ import annotations
import random
import math
from typing import Tuple, List

Pos = Tuple[int, int]


def manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def poisson(lmbda: float, rng: random.Random) -> int:
    """Poisson(λ) через алгоритм Кнута."""
    if lmbda <= 0:
        return 0
    L = math.exp(-lmbda)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= rng.random()
    return k - 1


def choice_weighted(items: List[Pos], weights: List[float], rng: random.Random) -> Pos:
    s = sum(weights)
    if s <= 0:
        return rng.choice(items)
    r = rng.random() * s
    acc = 0.0
    for it, w in zip(items, weights):
        acc += w
        if acc >= r:
            return it
    return items[-1]
