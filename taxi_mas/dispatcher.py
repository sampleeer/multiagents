from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import random

from .agents import Driver, Request
from .city import CityGrid
from .utils import Pos


@dataclass
class DispatchDecision:
    rid: int
    did: int
    price: float


@dataclass
class Dispatcher:
    """Диспетчер/маркетплейс: делает matching + surge pricing."""
    city: CityGrid
    base_fare: float = 2.0
    per_step_fare: float = 0.6
    surge_k: float = 0.8

    def surge_multiplier(self, n_open: int, n_idle: int) -> float:
        if n_idle <= 0:
            return 1.0 + self.surge_k * min(3.0, n_open / 1.0)
        ratio = n_open / max(1, n_idle)
        return 1.0 + self.surge_k * math.tanh(ratio - 1.0)

    def trip_price(self, origin: Pos, dest: Pos, surge: float) -> float:
        d = self.city.distance(origin, dest)
        return surge * (self.base_fare + self.per_step_fare * d)

    def match(self,
              drivers: Dict[int, Driver],
              requests: Dict[int, Request],
              strategy: str,
              rng: random.Random) -> List[DispatchDecision]:

        open_reqs = [r for r in requests.values() if r.is_open]
        idle_drivers = [d for d in drivers.values() if d.is_idle()]

        if not open_reqs or not idle_drivers:
            return []

        surge = self.surge_multiplier(len(open_reqs), len(idle_drivers))

        if strategy == "greedy":
            return self._match_greedy(idle_drivers, open_reqs, surge)
        if strategy == "auction":
            return self._match_auction(idle_drivers, open_reqs, surge, rng)

        raise ValueError(f"Unknown strategy: {strategy}")

    def _match_greedy(self, idle_drivers: List[Driver], open_reqs: List[Request], surge: float) -> List[DispatchDecision]:
        decisions: List[DispatchDecision] = []
        available = {d.did: d for d in idle_drivers}

        open_reqs_sorted = sorted(open_reqs, key=lambda r: r.created_at)
        for r in open_reqs_sorted:
            if not available:
                break
            best_did = min(available.keys(), key=lambda did: self.city.distance(available[did].pos, r.origin))
            d = available.pop(best_did)
            price = self.trip_price(r.origin, r.dest, surge)
            decisions.append(DispatchDecision(rid=r.rid, did=d.did, price=price))
        return decisions

    def _match_auction(self,
                      idle_drivers: List[Driver],
                      open_reqs: List[Request],
                      surge: float,
                      rng: random.Random) -> List[DispatchDecision]:
        remaining_reqs = list(open_reqs)
        remaining_drivers = {d.did: d for d in idle_drivers}
        decisions: List[DispatchDecision] = []

        # "предпочтения" водителя в ставке:
        alpha_pickup = 1.0
        beta_trip = 0.15
        gamma_random = 0.05

        while remaining_reqs and remaining_drivers:
            best_for_req: Dict[int, Tuple[int, float]] = {}  # rid -> (did, cost)

            for r in remaining_reqs:
                best_did: Optional[int] = None
                best_cost: float = float("inf")
                for did, d in remaining_drivers.items():
                    pickup = self.city.distance(d.pos, r.origin)
                    trip = self.city.distance(r.origin, r.dest)

                    cost = alpha_pickup * pickup + beta_trip * trip
                    cost *= 1.0 + gamma_random * (rng.random() - 0.5)

                    if cost < best_cost:
                        best_cost = cost
                        best_did = did

                if best_did is not None:
                    best_for_req[r.rid] = (best_did, best_cost)

            if not best_for_req:
                break

            by_driver: Dict[int, List[Tuple[int, float]]] = {}
            for rid, (did, cost) in best_for_req.items():
                by_driver.setdefault(did, []).append((rid, cost))

            assigned_rids = set()
            used_drivers = set()

            for did, items in by_driver.items():
                items.sort(key=lambda x: x[1])
                rid_best, _ = items[0]
                assigned_rids.add(rid_best)
                used_drivers.add(did)

            new_remaining_reqs = []
            for r in remaining_reqs:
                if r.rid in assigned_rids and r.rid in best_for_req:
                    did, _ = best_for_req[r.rid]
                    price = self.trip_price(r.origin, r.dest, surge)
                    decisions.append(DispatchDecision(rid=r.rid, did=did, price=price))
                else:
                    new_remaining_reqs.append(r)

            for did in used_drivers:
                remaining_drivers.pop(did, None)

            remaining_reqs = new_remaining_reqs

        return decisions
