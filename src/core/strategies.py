"""TV2 - Hai chiến lược tìm tài xế: A1 (Dijkstra từng tài xế) và A2 (Dijkstra đảo chiều)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .road_graph import RoadGraph


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

    def find_driver(self, graph, pickup_node, free_drivers) -> MatchResult:
        raise NotImplementedError  # TODO(TV2)


class ReverseDijkstra(MatchStrategy):
    """A2: Dijkstra trên đồ thị đảo chiều từ điểm đón, dừng ở tài xế rảnh đầu tiên."""
    name = "A2 - Dijkstra đảo chiều"

    def find_driver(self, graph, pickup_node, free_drivers) -> MatchResult:
        raise NotImplementedError  # TODO(TV2)
