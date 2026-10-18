"""TV2 - Đồ thị giao thông có hướng, trọng số = thời gian di chuyển."""
from __future__ import annotations

import math


class RoadGraph:
    def __init__(self) -> None:
        self._adj: dict[str, list[tuple[str, float]]] = {}
        self._reversed_cache: RoadGraph | None = None

    def add_node(self, node_id: str) -> None:
        if not isinstance(node_id, str):
            raise TypeError("node id must be a string")
        if node_id not in self._adj:
            self._adj[node_id] = []
            self._reversed_cache = None

    def has_node(self, node_id: str) -> bool:
        return node_id in self._adj

    def add_edge(self, u: str, v: str, weight: float) -> None:
        if not isinstance(u, str) or not isinstance(v, str):
            raise TypeError("edge endpoints must be strings")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise TypeError("edge weight must be a number")
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("edge weight must be finite and non-negative")

        self.add_node(u)
        self.add_node(v)
        self._adj[u].append((v, float(weight)))
        self._reversed_cache = None

    def nodes(self) -> list[str]:
        return list(self._adj)

    def edges(self) -> list[tuple[str, str, float]]:
        return [
            (u, v, weight)
            for u, adjacent in self._adj.items()
            for v, weight in adjacent
        ]

    def neighbors(self, u: str) -> list[tuple[str, float]]:
        return list(self._adj.get(u, ()))

    def reversed(self) -> "RoadGraph":
        """Đồ thị đảo chiều cạnh (dùng cho A2), có cơ chế cache để tối ưu hiệu năng."""
        if self._reversed_cache is not None:
            return self._reversed_cache
        reverse_graph = RoadGraph()
        for node_id in self._adj:
            reverse_graph.add_node(node_id)
        for u, v, weight in self.edges():
            reverse_graph.add_edge(v, u, weight)
        self._reversed_cache = reverse_graph
        return reverse_graph
