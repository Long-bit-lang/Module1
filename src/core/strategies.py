"""TV2 - Hai chiến lược tìm tài xế: A1 (Dijkstra từng tài xế) và A2 (Dijkstra đảo chiều)."""
from __future__ import annotations

import heapq
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import TypeAlias

from .road_graph import RoadGraph

_HeapEntry: TypeAlias = tuple[float, str]


@dataclass
class MatchResult:
    driver_id: str | None
    eta: float | None
    visited_count: int
    path: list[str] | None = None
    runtime_ms: float = 0.0


class MatchStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def find_driver(self, graph: RoadGraph, pickup_node: str,
                    free_drivers: dict[str, str]) -> MatchResult:
        """free_drivers: {driver_id: node hiện tại}."""


class DijkstraPerDriver(MatchStrategy):
    """A1: chạy Dijkstra từ từng tài xế rảnh đến điểm đón, chọn ETA nhỏ nhất."""
    name = "A1 - Dijkstra từng tài xế"

    def find_driver(
        self,
        graph: RoadGraph,
        pickup_node: str,
        free_drivers: dict[str, str],
    ) -> MatchResult:
        started_at = perf_counter()
        best_driver: str | None = None
        best_eta: float | None = None
        best_path: list[str] | None = None
        visited_count = 0

        if graph.has_node(pickup_node):
            for driver_id, start_node in sorted(free_drivers.items()):
                if not graph.has_node(start_node):
                    continue

                eta, path, visited = _shortest_path(graph, start_node, pickup_node)
                visited_count += visited
                if eta is None:
                    continue
                if best_eta is None or eta < best_eta or (
                    eta == best_eta and driver_id < best_driver
                ):
                    best_driver = driver_id
                    best_eta = eta
                    best_path = path

        return MatchResult(
            driver_id=best_driver,
            eta=best_eta,
            visited_count=visited_count,
            path=best_path,
            runtime_ms=(perf_counter() - started_at) * 1000,
        )


class ReverseDijkstra(MatchStrategy):
    """A2: Dijkstra từ điểm đón trên đồ thị đảo chiều."""
    name = "A2 - Dijkstra đảo chiều"

    def find_driver(
        self,
        graph: RoadGraph,
        pickup_node: str,
        free_drivers: dict[str, str],
    ) -> MatchResult:
        started_at = perf_counter()
        if not graph.has_node(pickup_node):
            return MatchResult(
                driver_id=None,
                eta=None,
                visited_count=0,
                path=None,
                runtime_ms=(perf_counter() - started_at) * 1000,
            )

        drivers_by_node: dict[str, list[str]] = {}
        for driver_id, node_id in free_drivers.items():
            if graph.has_node(node_id):
                drivers_by_node.setdefault(node_id, []).append(driver_id)

        if not drivers_by_node:
            return MatchResult(
                driver_id=None,
                eta=None,
                visited_count=0,
                path=None,
                runtime_ms=(perf_counter() - started_at) * 1000,
            )

        reverse_graph = graph.reversed()
        distances: dict[str, float] = {pickup_node: 0.0}
        next_hop: dict[str, str] = {}
        heap: list[_HeapEntry] = [(0.0, pickup_node)]
        visited_count = 0
        best_eta: float | None = None

        while heap:
            if best_eta is not None and heap[0][0] > best_eta:
                break
            distance, node_id = heapq.heappop(heap)
            visited_count += 1
            if distance != distances.get(node_id):
                continue

            if node_id in drivers_by_node:
                best_eta = distance

            for neighbor, weight in reverse_graph.neighbors(node_id):
                candidate = distance + weight
                if candidate < distances.get(neighbor, float("inf")):
                    distances[neighbor] = candidate
                    next_hop[neighbor] = node_id
                    heapq.heappush(heap, (candidate, neighbor))

        if best_eta is None:
            return MatchResult(
                driver_id=None,
                eta=None,
                visited_count=visited_count,
                path=None,
                runtime_ms=(perf_counter() - started_at) * 1000,
            )

        candidate_drivers = [
            driver_id
            for node_id, driver_ids in drivers_by_node.items()
            if distances.get(node_id) == best_eta
            for driver_id in driver_ids
        ]
        best_driver = min(candidate_drivers)
        start_node = free_drivers[best_driver]
        path = [start_node]
        while path[-1] != pickup_node:
            path.append(next_hop[path[-1]])

        return MatchResult(
            driver_id=best_driver,
            eta=best_eta,
            visited_count=visited_count,
            path=path,
            runtime_ms=(perf_counter() - started_at) * 1000,
        )


def _shortest_path(
    graph: RoadGraph,
    start_node: str,
    target_node: str,
) -> tuple[float | None, list[str] | None, int]:
    distances: dict[str, float] = {start_node: 0.0}
    previous: dict[str, str] = {}
    heap: list[_HeapEntry] = [(0.0, start_node)]
    visited_count = 0

    while heap:
        distance, node_id = heapq.heappop(heap)
        visited_count += 1
        if distance != distances.get(node_id):
            continue
        if node_id == target_node:
            path = [target_node]
            while path[-1] != start_node:
                path.append(previous[path[-1]])
            path.reverse()
            return distance, path, visited_count

        for neighbor, weight in graph.neighbors(node_id):
            candidate = distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = node_id
                heapq.heappush(heap, (candidate, neighbor))

    return None, None, visited_count


STRATEGIES: dict[str, type[MatchStrategy]] = {
    DijkstraPerDriver.name: DijkstraPerDriver,
    ReverseDijkstra.name: ReverseDijkstra,
}