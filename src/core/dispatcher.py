"""Business coordinator: requests, drivers, trips and dispatch undo/redo.

No file I/O here: JsonStorage and the UI are responsible for persistence.
The public method signatures follow docs/CONTRACT.md.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite

from models import ASSIGNED, BUSY, COMPLETED, FREE, QUEUED
from models.driver import Driver
from models.location import Location
from models.ride_request import RideRequest
from models.trip import Trip
from .road_graph import RoadGraph
from .strategies import MatchResult, MatchStrategy, shortest_path
from .structures import RequestQueue
from .undo_manager import DispatchAction, UndoManager


EMPTY_QUEUE, NO_FREE_DRIVER, NO_ROUTE = "empty_queue", "no_free_driver", "no_route"
def _next_number(prefix: str, ids) -> int:
    """Find the next unused sequential number after existing IDs."""
    values = [
        int(value[len(prefix):])
        for value in ids
        if isinstance(value, str)
        and value.startswith(prefix)
        and value[len(prefix):].isdigit()
    ]
    return max(values, default=0) + 1


class Dispatcher:
    def __init__(
        self,
        graph: RoadGraph,
        drivers: dict[str, Driver],
        trips: list[Trip] | None = None,
        all_requests: dict[str, RideRequest] | None = None,
   ) -> None:
        self.graph = graph
        self.drivers = dict(drivers)
        self.trips = list(trips) if trips is not None else []
        self.all_requests = dict(all_requests) if all_requests is not None else {}
        self.locations: dict[str, Location] = {}

        self.queue = RequestQueue()
        for request in self.all_requests.values():
            if request.status == QUEUED:
                self.queue.enqueue(request)
        self.undo_manager = UndoManager()

        # Optional information for UI; no change to CONTRACT signatures.
        self.last_match_result: MatchResult | None = None
        self._next_driver_id = _next_number('D', self.drivers)
        self._next_request_id = _next_number('R', self.all_requests)
        self._next_trip_id = _next_number('T', (trip.id for trip in self.trips))
        self.last_failure: str | None = None

    def _check_node(self, node: str) -> None:
        if not self.graph.has_node(node):
            raise ValueError(f"Đỉnh {node!r} không tồn tại trên đồ thị")

    def submit_request(self, pickup_node: str, dropoff_node: str) -> RideRequest:
        self._check_node(pickup_node)
        self._check_node(dropoff_node)
        if pickup_node == dropoff_node:
            raise ValueError("Điểm đón và điểm trả phải khác nhau")
        if shortest_path(self.graph, pickup_node, dropoff_node)[0] is None:
            raise ValueError(f"Không có đường đi từ {pickup_node} đến {dropoff_node}")
        request = RideRequest(f"R{self._next_request_id}", pickup_node, dropoff_node)
        self.all_requests[request.id] = request
        self.queue.enqueue(request)
        self._next_request_id += 1
        return request

    def add_driver(self, name: str, node: str) -> Driver:
        self._check_node(node)
        driver = Driver(f'D{self._next_driver_id}', name, node)
        self.drivers[driver.id] = driver
        self._next_driver_id += 1
        return driver

    def update_driver(self, driver_id, name=None, node=None) -> Driver:
        driver = self.drivers.get(driver_id)
        if driver is None:
            raise ValueError(f"Không có tài xế {driver_id}")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("Tên tài xế không được để trống")
        if node is not None:
            self._check_node(node)
            if driver.status == BUSY and node != driver.node:
                raise ValueError(f"Tài xế {driver_id} đang bận, không thể đổi vị trí")
        if name is not None:
            driver.name = name.strip()
        if node is not None:
            driver.node = node
        return driver


    def remove_driver(self, driver_id: str) -> bool:
        driver = self.drivers.get(driver_id)
        if driver is None:
            return False
        if driver.status == BUSY:
            raise ValueError(f'Tài xế {driver_id} đang bận')
        # Historical Trips would keep dangling driver IDs after deletion.
        # Discuss this extra guard with Long/Thang before final integration.
        if any(trip.driver_id == driver_id for trip in self.trips):
            raise ValueError(f'Tài xế {driver_id} đang được tham chiếu bởi lịch sử chuyến')
        if any(
            a.driver_id == driver_id
            for a in self._history_actions()
        ):
            raise ValueError(f'Tài xế {driver_id} còn lịch sử Undo/Redo')
        del self.drivers[driver_id]
        return True

    def _history_actions(self):
        """Read stack contents without modifying them (used for safe deletion)."""
        for stack in (self.undo_manager.undo_stack, self.undo_manager.redo_stack):
            items = []
            while len(stack):
                items.append(stack.pop())
            for item in reversed(items):
                stack.push(item)
            yield from items

    def dispatch_next(self, strategy: MatchStrategy) -> Trip | None:
        self.last_match_result, self.last_failure = None, None
        request = self.queue.peek()
        if request is None:
            self.last_failure = EMPTY_QUEUE
            return None
        free_drivers = {i: d.node for i, d in self.drivers.items() if d.status == FREE}
        if not free_drivers:
            self.last_failure = NO_FREE_DRIVER
            return None
        result = strategy.find_driver(self.graph, request.pickup_node, free_drivers)
        self.last_match_result = result
        if result.driver_id is None or result.eta is None:
            self.last_failure = NO_ROUTE
            return None
        if result.driver_id not in free_drivers:
            raise ValueError('Chiến lược trả về tài xế không rảnh / không tồn tại')
        if isinstance(result.eta, bool) or not isfinite(result.eta) or result.eta < 0:
            raise ValueError('Chiến lược trả về ETA không hợp lệ')

        driver = self.drivers[result.driver_id]
        trip = Trip(f'T{self._next_trip_id}', request.id, driver.id, result.eta)
        old_node = driver.node
        # Prepare the whole transaction before changing the queue.
        driver.assign()
        removed_request = self.queue.dequeue()
        assert removed_request is request
        request.status = ASSIGNED
        self.trips.append(trip)
        self.undo_manager.record(
            DispatchAction(
                trip=trip,
                driver_id=driver.id,
                request=request,
                previous_driver_node=old_node,
            )
        )
        self._next_trip_id += 1
        return trip

    def dispatch_all(self, strategy: MatchStrategy) -> list[Trip]:
        trips: list[Trip] = []
        while (trip := self.dispatch_next(strategy)) is not None:
            trips.append(trip)
        return trips

    def ride_estimate(self, request_id: str) -> tuple[float, list[str]] | None:
        req = self.all_requests.get(request_id)
        if req is None:
            return None
        eta, path, _ = shortest_path(self.graph, req.pickup_node, req.dropoff_node)
        return None if eta is None else (eta, path)

    def complete_trip(self, trip_id: str) -> bool:
        trip = next((trip for trip in self.trips if trip.id == trip_id), None)
        if trip is None or trip.status == COMPLETED:
            return False
        driver = self.drivers[trip.driver_id]
        request = self.all_requests[trip.request_id]
        driver.node = request.dropoff_node
        driver.release()
        trip.status = COMPLETED
        self.undo_manager.undo_stack.clear()
        self.undo_manager.redo_stack.clear()
        return True

    def _peek_action(self, stack) -> DispatchAction | None:
        if len(stack) == 0:
            return None
        action = stack.pop()
        stack.push(action)
        return action

    def can_undo(self) -> bool:
        action = self._peek_action(self.undo_manager.undo_stack)
        # A completed trip cannot be 'uncompleted' by dispatch-only undo.
        return action is not None and action.trip.status != COMPLETED

    def can_redo(self) -> bool:
        action = self._peek_action(self.undo_manager.redo_stack)
        if action is None:
            return False
        driver = self.drivers.get(action.driver_id)
        head = self.queue.peek()
        return (
            driver is not None
            and driver.status == FREE
            and head is not None
            and head.id == action.request.id
            and action.request.status == QUEUED
            and not any(trip.id == action.trip.id for trip in self.trips)
        )

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        action = self.undo_manager.undo()
        assert action is not None
        self.trips = [trip for trip in self.trips if trip.id != action.trip.id]
        driver = self.drivers[action.driver_id]
        driver.release()
        if action.previous_driver_node is not None:
            driver.node = action.previous_driver_node
        action.request.status = QUEUED
        self.queue.requeue_head(action.request)
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        action = self.undo_manager.redo()
        assert action is not None
        request = self.queue.dequeue()
        assert request.id == action.request.id
        self.drivers[action.driver_id].assign()
        action.request.status = ASSIGNED
        self.trips.append(action.trip)
        return True

    def queue_snapshot(self) -> list[RideRequest]:
        return deepcopy(list(self.queue))

    def trips_snapshot(self) -> list[Trip]:
        return deepcopy(self.trips)

    def drivers_snapshot(self) -> dict[str, Driver]:
        return deepcopy(self.drivers)

    @classmethod
    def from_state(cls, state: dict) -> 'Dispatcher':
        # JsonStorage.load_all returns domain objects, not raw JSON strings.
        requests = state.get('requests', [])
        all_requests = {request.id: request for request in requests}
        if len(all_requests) != len(requests):
            raise ValueError('Trùng ID yêu cầu trong state')
        dispatcher = cls(
            graph=state['graph'],
            drivers=state['drivers'],
            trips=state.get('trips', []),
            all_requests=all_requests,
        )
        dispatcher.locations = dict(state.get('locations', {}))
        return dispatcher

    def export_state(self) -> dict:
        # Put queued requests first in CURRENT FIFO order so load_all/from_state
        # reconstructs the same queue (including requeue_head after Undo).
        queued = list(self.queue)
        queued_ids = {request.id for request in queued}
        other_requests = [
            request for request in self.all_requests.values()
            if request.id not in queued_ids
        ]
        return {
            'graph': self.graph,
            'drivers': self.drivers,
            'requests': queued + other_requests,
            'trips': list(self.trips),
            'locations': self.locations,
        }
