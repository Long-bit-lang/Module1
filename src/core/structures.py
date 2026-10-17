"""Queue (FIFO) and Stack (LIFO) implemented with linked nodes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from models.ride_request import RideRequest


@dataclass
class _Node:
    value: Any
    next: _Node | None = None


class RequestQueue:
    def __init__(self) -> None:
        self._head: _Node | None = None
        self._tail: _Node | None = None
        self._size = 0

    def enqueue(self, request: RideRequest) -> None:
        node = _Node(request)
        if self._tail is None:
            self._head = node
        else:
            self._tail.next = node
        self._tail = node
        self._size += 1

    def dequeue(self) -> RideRequest:
        if self._head is None:
            raise IndexError("Khong the dequeue hang doi rong")
        request = self._head.value
        self._head = self._head.next
        if self._head is None:
            self._tail = None
        self._size -= 1
        return request

    def peek(self) -> RideRequest | None:
        return None if self._head is None else self._head.value

    def requeue_head(self, request: RideRequest) -> None:
        self._head = _Node(request, self._head)
        if self._tail is None:
            self._tail = self._head
        self._size += 1

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[RideRequest]:
        node = self._head
        while node is not None:
            yield node.value
            node = node.next


class Stack:
    def __init__(self) -> None:
        self._top: _Node | None = None
        self._size = 0

    def push(self, item: Any) -> None:
        self._top = _Node(item, self._top)
        self._size += 1

    def pop(self) -> Any:
        if self._top is None:
            raise IndexError("Khong the pop ngan xep rong")
        item = self._top.value
        self._top = self._top.next
        self._size -= 1
        return item

    def clear(self) -> None:
        self._top = None
        self._size = 0

    def __len__(self) -> int:
        return self._size
