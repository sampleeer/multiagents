from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import statistics

from .agents import Driver, Request


@dataclass
class Metrics:
    wait_times: List[int] = field(default_factory=list)
    trip_times: List[int] = field(default_factory=list)
    canceled: int = 0
    completed: int = 0
    prices: List[float] = field(default_factory=list)

    def record_completed(self, r: Request, price: float):
        if r.picked_up_at is not None and r.dropped_off_at is not None:
            self.wait_times.append(r.picked_up_at - r.created_at)
            self.trip_times.append(r.dropped_off_at - r.picked_up_at)
            self.completed += 1
            self.prices.append(price)

    def record_canceled(self):
        self.canceled += 1

    def summary(self, drivers: Dict[int, Driver]) -> Dict[str, float]:
        util = []
        income = []
        for d in drivers.values():
            total = d.idle_ticks + d.busy_ticks
            util.append((d.busy_ticks / total) if total else 0.0)
            income.append(d.total_income)

        return {
            "completed": float(self.completed),
            "canceled": float(self.canceled),
            "cancel_rate": (self.canceled / max(1, self.canceled + self.completed)),
            "avg_wait": statistics.mean(self.wait_times) if self.wait_times else 0.0,
            "p95_wait": statistics.quantiles(self.wait_times, n=20)[-1] if len(self.wait_times) >= 20 else (max(self.wait_times) if self.wait_times else 0.0),
            "avg_trip_time": statistics.mean(self.trip_times) if self.trip_times else 0.0,
            "avg_price": statistics.mean(self.prices) if self.prices else 0.0,
            "avg_driver_util": statistics.mean(util) if util else 0.0,
            "avg_driver_income": statistics.mean(income) if income else 0.0,
            "max_driver_income": max(income) if income else 0.0,
        }
