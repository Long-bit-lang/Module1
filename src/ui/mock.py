"""TV5 - Backend giả lập chạy trong bộ nhớ, đúng chữ ký CONTRACT.

Chỉ dùng khi Dispatcher/JsonStorage/STRATEGIES thật chưa sẵn sàng (hoặc ép bằng biến môi
trường RIDE_DISPATCH_BACKEND=mock). KHÔNG phải nơi chứa logic nghiệp vụ của dự án.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from core.road_graph import RoadGraph
from core.strategies import STRATEGIES, MatchResult, shortest_path
from models import ASSIGNED, BUSY, COMPLETED, FREE, QUEUED


# ----------------------------------------------------------------- thực thể giả
@dataclass
class MockDriver:
    id: str
    name: str
    node: str
    status: str = FREE


@dataclass
class MockRequest:
    id: str
    pickup_node: str
    dropoff_node: str
    status: str = QUEUED


@dataclass
class MockTrip:
    id: str
    request_id: str
    driver_id: str
    eta: float
    status: str = ASSIGNED


# ----------------------------------------------------------------- bộ điều phối giả
class FakeDispatcher:
    def __init__(self, graph: RoadGraph, drivers: dict[str, MockDriver], locations: dict[str, str] | None = None):
        self.graph = graph
        self.drivers = drivers
        self.locations = locations or {}
        self.trips: list[MockTrip] = []
        self.all_requests: dict[str, MockRequest] = {}
        self.queue: list[MockRequest] = []
        self._undo: list = []
        self._redo: list = []
        self._seq = {"R": 0, "T": 0, "D": len(drivers)}
        self.last_match_result: MatchResult | None = None
        self.last_failure: str | None = None

    def _new_id(self, prefix: str) -> str:
        self._seq[prefix] += 1
        return f"{prefix}{self._seq[prefix]}"

    def _check_node(self, node: str) -> None:
        if not self.graph.has_node(node):
            raise ValueError(f"Đỉnh không tồn tại: {node}")

    # --- yêu cầu
    def submit_request(self, pickup_node: str, dropoff_node: str) -> MockRequest:
        self._check_node(pickup_node)
        self._check_node(dropoff_node)
        if pickup_node == dropoff_node:
            raise ValueError("Điểm đón và điểm trả phải khác nhau")
        if shortest_path(self.graph, pickup_node, dropoff_node)[0] is None:
            raise ValueError(f"Không có đường đi từ {pickup_node} đến {dropoff_node}")
        req = MockRequest(self._new_id("R"), pickup_node, dropoff_node)
        self.all_requests[req.id] = req
        self.queue.append(req)
        return req

    # --- tài xế
    def add_driver(self, name: str, node: str) -> MockDriver:
        if not name.strip():
            raise ValueError("Tên tài xế không được để trống")
        self._check_node(node)
        drv = MockDriver(self._new_id("D"), name.strip(), node)
        self.drivers[drv.id] = drv
        return drv

    def update_driver(self, driver_id, name=None, node=None) -> MockDriver:
        drv = self.drivers.get(driver_id)
        if drv is None:
            raise ValueError(f"Không có tài xế {driver_id}")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("Tên tài xế không được để trống")
        if node is not None:
            self._check_node(node)
            if drv.status == BUSY and node != drv.node:
                raise ValueError(f"Tài xế {driver_id} đang bận, không thể đổi vị trí")
            drv.node = node
        if name is not None:
            drv.name = name.strip()
        return drv

    def remove_driver(self, driver_id: str) -> bool:
        drv = self.drivers.get(driver_id)
        if drv is None:
            return False
        if drv.status == BUSY:
            raise ValueError(f"Tài xế {driver_id} đang bận")
        del self.drivers[driver_id]
        return True

    # --- điều phối
    def dispatch_next(self, strategy) -> MockTrip | None:
        self.last_match_result, self.last_failure = None, None
        if not self.queue:
            self.last_failure = "empty_queue"
            return None
        req = self.queue[0]
        free = {d.id: d.node for d in self.drivers.values() if d.status == FREE}
        if not free:
            self.last_failure = "no_free_driver"
            return None
        res = strategy.find_driver(self.graph, req.pickup_node, free)
        self.last_match_result = res
        if res.driver_id is None or res.eta is None:
            self.last_failure = "no_route"
            return None
        self.queue.pop(0)
        req.status = ASSIGNED
        self.drivers[res.driver_id].status = BUSY
        trip = MockTrip(self._new_id("T"), req.id, res.driver_id, res.eta)
        self.trips.append(trip)
        self._undo.append((trip, res.driver_id, req))
        self._redo.clear()
        return trip

    def dispatch_all(self, strategy) -> list[MockTrip]:
        trips = []
        while (trip := self.dispatch_next(strategy)) is not None:
            trips.append(trip)
        return trips

    def cancel_request(self, request_id: str) -> bool:
        req = self.all_requests.get(request_id)
        if req is None or req.status != QUEUED:
            return False
        self.queue = [r for r in self.queue if r.id != request_id]
        del self.all_requests[request_id]
        return True

    def ride_estimate(
        self, request_id_or_pickup: str, dropoff_node: str | None = None
    ) -> tuple[float, list[str]] | None:
        if dropoff_node is not None:
            pickup_node = request_id_or_pickup
            if not self.graph.has_node(pickup_node) or not self.graph.has_node(dropoff_node):
                return None
            eta, path, _ = shortest_path(self.graph, pickup_node, dropoff_node)
            return None if eta is None else (eta, path)
        req = self.all_requests.get(request_id_or_pickup)
        if req is None:
            return None
        eta, path, _ = shortest_path(self.graph, req.pickup_node, req.dropoff_node)
        return None if eta is None else (eta, path)

    def complete_trip(self, trip_id: str) -> bool:
        trip = next((t for t in self.trips if t.id == trip_id), None)
        if trip is None or trip.status != ASSIGNED:
            return False
        trip.status = COMPLETED
        drv = self.drivers[trip.driver_id]
        drv.status = FREE
        drv.node = self.all_requests[trip.request_id].dropoff_node
        self._undo.clear()
        self._redo.clear()
        return True

    # --- undo / redo
    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        trip, driver_id, req = self._undo.pop()
        self.trips.remove(trip)
        self.drivers[driver_id].status = FREE
        req.status = QUEUED
        self.queue.insert(0, req)
        self._redo.append((trip, driver_id, req))
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        trip, driver_id, req = self._redo.pop()
        self.queue.remove(req)
        req.status = ASSIGNED
        self.drivers[driver_id].status = BUSY
        self.trips.append(trip)
        self._undo.append((trip, driver_id, req))
        return True

    # --- snapshot & trạng thái
    def queue_snapshot(self):
        return [copy.copy(r) for r in self.queue]

    def trips_snapshot(self):
        return [copy.copy(t) for t in self.trips]

    def drivers_snapshot(self):
        return {k: copy.copy(v) for k, v in self.drivers.items()}

    def export_state(self) -> dict:
        return {
            "graph": self.graph,
            "drivers": self.drivers,
            "requests": list(self.all_requests.values()),
            "trips": self.trips,
            "locations": self.locations,
        }


class FakeStorage:
    """Không ghi đĩa; chỉ đếm số lần lưu để kiểm thử UI có tự động lưu hay không."""

    def __init__(self):
        self.save_count = 0
        self.last_state: dict | None = None

    def load_all(self) -> dict:
        raise NotImplementedError("FakeStorage không nạp từ đĩa; dùng build_mock()")

    def save_all(self, state: dict) -> None:
        self.save_count += 1
        self.last_state = state


def build_mock():
    """Trả về (storage, dispatcher, strategies, locations) với dữ liệu mẫu Đà Nẵng."""
    names = {
        "N1": "Bến xe Trung tâm",
        "N2": "ĐH Bách Khoa",
        "N3": "Cầu Rồng",
        "N4": "Chợ Hàn",
        "N5": "Ga Đà Nẵng",
        "N6": "Sân bay Đà Nẵng",
        "N7": "Biển Mỹ Khê",
        "N8": "Ngũ Hành Sơn",
    }
    g = RoadGraph()
    for n in names:
        g.add_node(n)
    for u, v, w in [
        ("N1", "N2", 5),
        ("N2", "N3", 4),
        ("N3", "N4", 6),
        ("N4", "N5", 3),
        ("N5", "N6", 7),
        ("N6", "N7", 4),
        ("N7", "N8", 5),
        ("N8", "N1", 8),
        ("N2", "N6", 9),
        ("N3", "N7", 5),
    ]:
        g.add_edge(u, v, w)
        g.add_edge(v, u, w)
    g.add_edge("N4", "N1", 4)  # đường một chiều
    drivers = {
        "D1": MockDriver("D1", "An", "N1"),
        "D2": MockDriver("D2", "Bình", "N4"),
        "D3": MockDriver("D3", "Chi", "N6"),
    }
    strategies = {name: cls() for name, cls in STRATEGIES.items()}
    return FakeStorage(), FakeDispatcher(g, drivers, names), strategies, names
