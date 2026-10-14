"""TV3 - Đầu mối nghiệp vụ: hàng đợi, gọi chiến lược, tạo Trip, Undo/Redo.
Không đọc/ghi file trực tiếp (việc đó thuộc JsonStorage)."""
from __future__ import annotations

from models.trip import Trip
from models.ride_request import RideRequest
from .road_graph import RoadGraph
from .strategies import MatchStrategy
from .structures import RequestQueue
from .undo_manager import UndoManager


class Dispatcher:
    def __init__(self, graph: RoadGraph, drivers: dict, trips: list | None = None):
        self.graph = graph
        self.drivers = drivers          # {driver_id: Driver}
        self.trips = trips or []
        self.queue = RequestQueue()
        self.undo_manager = UndoManager()

    def submit_request(self, request: RideRequest) -> None:
        raise NotImplementedError  # TODO(TV3)

    def dispatch_next(self, strategy: MatchStrategy) -> Trip | None:
        """None nếu không có tài xế / không có đường đi; yêu cầu không bị mất."""
        raise NotImplementedError  # TODO(TV3)

    def undo(self) -> bool:
        raise NotImplementedError  # TODO(TV3)

    def redo(self) -> bool:
        raise NotImplementedError  # TODO(TV3)
