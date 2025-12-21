from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .utils import Pos

@dataclass
class Request:
    # 'Пассажир' в симуляции — это заявка.
    rid: int
    origin: Pos
    dest: Pos
    created_at: int
    patience: int

    assigned_driver: Optional[int] = None
    picked_up_at: Optional[int] = None
    dropped_off_at: Optional[int] = None
    canceled_at: Optional[int] = None

    @property
    def is_open(self) -> bool:
        return self.assigned_driver is None and self.canceled_at is None

    @property
    def is_active(self) -> bool:
        return self.assigned_driver is not None and self.dropped_off_at is None and self.canceled_at is None


@dataclass
class Driver:
    # Driver‑агент: idle / to_pickup / on_trip
    did: int
    pos: Pos

    state: str = "idle"
    target: Optional[Pos] = None
    current_request: Optional[int] = None

    total_income: float = 0.0
    idle_ticks: int = 0
    busy_ticks: int = 0

    rebalance_target: Optional[Pos] = None

    def is_idle(self) -> bool:
        return self.state == "idle" and self.current_request is None

    def tick_accounting(self):
        if self.state == "idle":
            self.idle_ticks += 1
        else:
            self.busy_ticks += 1
