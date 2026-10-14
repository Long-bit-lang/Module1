"""TV3 - Cấu trúc dữ liệu tự cài: Queue (FIFO) và Stack."""
from __future__ import annotations
from collections import deque
from typing import Any


class RequestQueue:
    def __init__(self):
        self._items: deque[Any] = deque()

    def enqueue(self, item: Any) -> None:
        raise NotImplementedError  # TODO(TV3)

    def dequeue(self) -> Any:
        raise NotImplementedError  # TODO(TV3)

    def peek(self) -> Any:
        raise NotImplementedError  # TODO(TV3)

    def __len__(self) -> int:
        return len(self._items)


class Stack:
    def __init__(self):
        self._items: list[Any] = []

    def push(self, item: Any) -> None:
        raise NotImplementedError  # TODO(TV3)

    def pop(self) -> Any:
        raise NotImplementedError  # TODO(TV3)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
