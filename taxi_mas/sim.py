from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import random

from .city import CityGrid
from .agents import Driver, Request
from .dispatcher import Dispatcher
from .metrics import Metrics
from .utils import poisson, Pos, choice_weighted


@dataclass
class SimConfig:
    steps: int = 800
    n_drivers: int = 35
    request_rate: float = 2.0
    grid_w: int = 25
    grid_h: int = 25
    patience_min: int = 20
    patience_max: int = 80
    dispatch_every: int = 2
    strategy: str = "auction"
    seed: int = 42

    rebalance_every: int = 15
    rebalance_strength: float = 0.7


class TaxiMAS:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)

        self.city = CityGrid(cfg.grid_w, cfg.grid_h)
        self.dispatcher = Dispatcher(self.city)

        self.drivers: Dict[int, Driver] = {}
        self.requests: Dict[int, Request] = {}
        self.metrics = Metrics()

        self.time: int = 0
        self._rid_seq = 1

        self.open_requests_ts: List[int] = []
        self.completed_ts: List[int] = []
        self.canceled_ts: List[int] = []
        self.avg_wait_ts: List[float] = []

        self._price_by_rid: Dict[int, float] = {}

    def init_agents(self):
        for did in range(1, self.cfg.n_drivers + 1):
            self.drivers[did] = Driver(did=did, pos=self.city.random_pos(self.rng))

    def _sample_demand_point(self) -> Pos:
        w, h = self.city.width, self.city.height
        hotspots = [
            (int(w * 0.25), int(h * 0.25)),
            (int(w * 0.75), int(h * 0.35)),
            (int(w * 0.55), int(h * 0.80)),
        ]
        points = [self.city.random_pos(self.rng) for _ in range(3)] + hotspots
        weights = [1.0, 1.0, 1.0, 4.0, 3.2, 3.6]
        return choice_weighted(points, weights, self.rng)

    def spawn_requests(self):
        k = poisson(self.cfg.request_rate, self.rng)
        for _ in range(k):
            origin = self._sample_demand_point()
            dest = self.city.random_pos(self.rng)
            while dest == origin:
                dest = self.city.random_pos(self.rng)

            patience = self.rng.randint(self.cfg.patience_min, self.cfg.patience_max)

            rid = self._rid_seq
            self._rid_seq += 1
            self.requests[rid] = Request(
                rid=rid,
                origin=origin,
                dest=dest,
                created_at=self.time,
                patience=patience,
            )

    def cancel_expired(self):
        for r in self.requests.values():
            if r.is_open and (self.time - r.created_at) > r.patience:
                r.canceled_at = self.time
                self.metrics.record_canceled()

    def dispatch(self):
        decisions = self.dispatcher.match(self.drivers, self.requests, self.cfg.strategy, self.rng)
        for dec in decisions:
            r = self.requests.get(dec.rid)
            d = self.drivers.get(dec.did)
            if not r or not d:
                continue
            if not r.is_open or not d.is_idle():
                continue

            r.assigned_driver = d.did
            d.current_request = r.rid
            d.state = "to_pickup"
            d.target = r.origin

            self._price_by_rid[r.rid] = dec.price

    def move_drivers(self):
        for d in self.drivers.values():
            d.tick_accounting()

            if d.state == "idle":
                if d.rebalance_target and d.pos != d.rebalance_target:
                    d.pos = self.city.step_towards(d.pos, d.rebalance_target)
                continue

            rid = d.current_request
            if rid is None:
                d.state = "idle"
                d.target = None
                continue

            r = self.requests.get(rid)
            if r is None:
                d.state = "idle"
                d.target = None
                d.current_request = None
                continue

            if r.canceled_at is not None:
                d.state = "idle"
                d.target = None
                d.current_request = None
                continue

            if d.state == "to_pickup":
                if d.pos != r.origin:
                    d.pos = self.city.step_towards(d.pos, r.origin)
                if d.pos == r.origin:
                    r.picked_up_at = self.time
                    d.state = "on_trip"
                    d.target = r.dest

            elif d.state == "on_trip":
                if d.pos != r.dest:
                    d.pos = self.city.step_towards(d.pos, r.dest)
                if d.pos == r.dest:
                    r.dropped_off_at = self.time
                    d.state = "idle"
                    d.target = None
                    d.current_request = None

                    price = self._price_by_rid.get(r.rid, 0.0)
                    d.total_income += price
                    self.metrics.record_completed(r, price)

    def rebalance(self):
        open_reqs = [r for r in self.requests.values() if r.is_open]
        if not open_reqs:
            for d in self.drivers.values():
                d.rebalance_target = None
            return

        cx = sum(r.origin[0] for r in open_reqs) / len(open_reqs)
        cy = sum(r.origin[1] for r in open_reqs) / len(open_reqs)
        hot = (int(round(cx)), int(round(cy)))

        for d in self.drivers.values():
            if d.is_idle():
                d.rebalance_target = hot if (self.rng.random() < self.cfg.rebalance_strength) else None

    def record_timeseries(self):
        open_n = sum(1 for r in self.requests.values() if r.is_open)
        self.open_requests_ts.append(open_n)
        self.completed_ts.append(self.metrics.completed)
        self.canceled_ts.append(self.metrics.canceled)
        self.avg_wait_ts.append((sum(self.metrics.wait_times) / len(self.metrics.wait_times)) if self.metrics.wait_times else 0.0)

    def step(self):
        self.spawn_requests()
        self.cancel_expired()

        if self.time % self.cfg.dispatch_every == 0:
            self.dispatch()

        if self.time % self.cfg.rebalance_every == 0:
            self.rebalance()

        self.move_drivers()
        self.record_timeseries()
        self.time += 1

    def run(self):
        self.init_agents()
        for _ in range(self.cfg.steps):
            self.step()
        return self.metrics.summary(self.drivers)
