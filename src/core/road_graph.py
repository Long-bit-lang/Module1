"""TV2 - Đồ thị giao thông có hướng, trọng số = thời gian di chuyển."""
from __future__ import annotations


class RoadGraph:
    def __init__(self):
        self._adj: dict[str, list[tuple[str, float]]] = {}

    def add_edge(self, u: str, v: str, weight: float) -> None:
        raise NotImplementedError  # TODO(TV2)

    def nodes(self) -> list[str]:
        raise NotImplementedError  # TODO(TV2)

    def neighbors(self, u: str) -> list[tuple[str, float]]:
        raise NotImplementedError  # TODO(TV2)

    def reversed(self) -> "RoadGraph":
        """Đồ thị đảo chiều cạnh (dùng cho A2)."""
        raise NotImplementedError  # TODO(TV2)
