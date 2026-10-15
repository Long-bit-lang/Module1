"""TV5 - Backend giả lập chạy trong bộ nhớ, đúng chữ ký CONTRACT.

Chỉ dùng khi Dispatcher/JsonStorage/STRATEGIES thật chưa sẵn sàng (hoặc ép bằng biến môi
trường RIDE_DISPATCH_BACKEND=mock). KHÔNG phải nơi chứa logic nghiệp vụ của dự án.
Hai chiến lược bên dưới chỉ để màn hình điều phối và benchmark có số liệu hiển thị.
"""
from __future__ import annotations

import copy
import heapq
import time
from dataclasses import dataclass

from core.strategies import MatchResult, MatchStrategy

FREE, BUSY = "free", "busy"
QUEUED, ASSIGNED, COMPLETED = "queued", "assigned", "completed"


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


class MockGraph:
    def __init__(self):
        self._adj: dict[str, list[tuple[str, float]]] = {}

    def add_node(self, id: str) -> None:
        self._adj.setdefault(id, [])

    def has_node(self, id: str) -> bool:
        return id in self._adj

    def add_edge(self, u: str, v: str, weight: float) -> None:
        if weight < 0:
            raise ValueError("weight phải >= 0")
        self.add_node(u)
        self.add_node(v)
        self._adj[u].append((v, float(weight)))

    def nodes(self) -> list[str]:
        return list(self._adj)

    def edges(self) -> list[tuple[str, str, float]]:
        return [(u, v, w) for u, outs in self._adj.items() for v, w in outs]

    def neighbors(self, u: str) -> list[tuple[str, float]]:
        return list(self._adj.get(u, []))

    def reversed(self) -> "MockGraph":
        rev = MockGraph()
        for n in self._adj:
            rev.add_node(n)
        for u, v, w in self.edges():
            rev.add_edge(v, u, w)
        return rev


# --------------------------------------------------------- chiến lược giả lập
def _dijkstra(graph, src, on_pop):
    """Dijkstra tối giản; đếm số đỉnh được chốt (pop hợp lệ). on_pop(u, d) -> True để dừng."""
    dist, prev, done = {src: 0.0}, {}, set()
    heap = [(0.0, src)]
    pops = 0
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        pops += 1
        if on_pop(u, d):
            break
        for v, w in graph.neighbors(u):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v], prev[v] = nd, u
                heapq.heappush(heap, (nd, v))
    return dist, prev, pops


def _walk(prev, start, src):
    path = [start]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return path


class MockDijkstraPerDriver(MatchStrategy):
    name = "A1 - Dijkstra từng tài xế"

    def find_driver(self, graph, pickup_node, free_drivers) -> MatchResult:
        t0 = time.perf_counter()
        best, visited = None, 0
        for did, node in sorted(free_drivers.items()):
            dist, prev, pops = _dijkstra(graph, node, lambda u, d: u == pickup_node)
            visited += pops
            if pickup_node in dist:
                key = (round(dist[pickup_node], 9), did)
                if best is None or key < best[0]:
                    best = (key, _walk(prev, pickup_node, node)[::-1])
        ms = (time.perf_counter() - t0) * 1000
        if best is None:
            return MatchResult(None, None, visited, None, ms)
        (eta, did), path = best
        return MatchResult(did, eta, visited, path, ms)


class MockReverseDijkstra(MatchStrategy):
    name = "A2 - Dijkstra đảo chiều"

    def find_driver(self, graph, pickup_node, free_drivers) -> MatchResult:
        t0 = time.perf_counter()
        at_node: dict[str, list[str]] = {}
        for did, node in free_drivers.items():
            at_node.setdefault(node, []).append(did)
        found: list[tuple[float, str, str]] = []  # (eta, driver_id, node)

        def on_pop(u, d):
            if found and d > found[0][0] + 1e-9:
                return True
            for did in at_node.get(u, []):
                found.append((round(d, 9), did, u))
            found.sort()
            return False

        _, prev, pops = _dijkstra(graph.reversed(), pickup_node, on_pop)
        ms = (time.perf_counter() - t0) * 1000
        if not found:
            return MatchResult(None, None, pops, None, ms)
        eta, did, node = found[0]
        return MatchResult(did, eta, pops, _walk(prev, node, pickup_node), ms)


# ------------------------------------------------------------ Dispatcher giả
class FakeDispatcher:
    """Mô phỏng đúng API công khai của Dispatcher trong CONTRACT mục 5."""

    def __init__(self, graph: MockGraph, drivers: dict, locations: dict | None = None):
        self.graph = graph
        self.drivers = drivers
        self.locations = locations or {}
        self.trips: list[MockTrip] = []
        self.all_requests: dict[str, MockRequest] = {}
        self.queue: list[MockRequest] = []
        self._undo: list = []
        self._redo: list = []
        self._seq = {"R": 0, "T": 0, "D": len(drivers)}

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
        req = MockRequest(self._new_id("R"), pickup_node, dropoff_node)
        self.all_requests[req.id] = req
        self.queue.append(req)
        return req

    # --- tài xế
    def add_driver(self, name: str, node: str) -> MockDriver:
        if not name.strip():
            raise ValueError("Tên tài xế không được rỗng")
        self._check_node(node)
        drv = MockDriver(self._new_id("D"), name.strip(), node)
        self.drivers[drv.id] = drv
        return drv

    def update_driver(self, driver_id, name=None, node=None) -> MockDriver:
        drv = self.drivers.get(driver_id)
        if drv is None:
            raise ValueError(f"Không có tài xế {driver_id}")
        if node is not None:
            self._check_node(node)
            drv.node = node
        if name is not None and name.strip():
            drv.name = name.strip()
        return drv

    def remove_driver(self, driver_id: str) -> bool:
        drv = self.drivers.get(driver_id)
        if drv is None:
            return False
        if drv.status == BUSY:
            raise ValueError("Không thể xóa tài xế đang bận")
        del self.drivers[driver_id]
        return True

    # --- điều phối
    def dispatch_next(self, strategy) -> MockTrip | None:
        if not self.queue:
            return None
        req = self.queue[0]
        free = {d.id: d.node for d in self.drivers.values() if d.status == FREE}
        if not free:
            return None
        res = strategy.find_driver(self.graph, req.pickup_node, free)
        if res.driver_id is None:
            return None
        self.queue.pop(0)
        req.status = ASSIGNED
        self.drivers[res.driver_id].status = BUSY
        trip = MockTrip(self._new_id("T"), req.id, res.driver_id, res.eta)
        self.trips.append(trip)
        self._undo.append((trip, res.driver_id, req))
        self._redo.clear()
        return trip

    def complete_trip(self, trip_id: str) -> bool:
        trip = next((t for t in self.trips if t.id == trip_id), None)
        if trip is None or trip.status != ASSIGNED:
            return False
        trip.status = COMPLETED
        drv = self.drivers[trip.driver_id]
        drv.status = FREE
        drv.node = self.all_requests[trip.request_id].dropoff_node
        # Đề xuất thiết kế: hoàn thành chuyến làm lịch sử Undo/Redo cũ không còn hợp lệ.
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
        "N1": "Bến xe Trung tâm", "N2": "ĐH Bách Khoa", "N3": "Cầu Rồng",
        "N4": "Chợ Hàn", "N5": "Ga Đà Nẵng", "N6": "Sân bay Đà Nẵng",
        "N7": "Biển Mỹ Khê", "N8": "Ngũ Hành Sơn",
    }
    g = MockGraph()
    for n in names:
        g.add_node(n)
    for u, v, w in [("N1", "N2", 5), ("N2", "N3", 4), ("N3", "N4", 6), ("N4", "N5", 3),
                    ("N5", "N6", 7), ("N6", "N7", 4), ("N7", "N8", 5), ("N8", "N1", 8),
                    ("N2", "N6", 9), ("N3", "N7", 5)]:
        g.add_edge(u, v, w)
        g.add_edge(v, u, w)
    g.add_edge("N4", "N1", 4)  # đường một chiều
    drivers = {
        "D1": MockDriver("D1", "An", "N1"),
        "D2": MockDriver("D2", "Bình", "N4"),
        "D3": MockDriver("D3", "Chi", "N6"),
    }
    strategies = {s.name: s for s in (MockDijkstraPerDriver(), MockReverseDijkstra())}
    return FakeStorage(), FakeDispatcher(g, drivers, names), strategies, names
