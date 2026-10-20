"""Min-heap"""

from __future__ import annotations

HeapEntry = tuple[float, str]


class MinHeap:
    def __init__(self) -> None:
        self._items: list[HeapEntry] = []

    def __bool__(self) -> bool:
        return bool(self._items)

    def push(self, item: HeapEntry) -> None:
        self._items.append(item)
        index = len(self._items) - 1

        while index > 0:
            parent = (index - 1) // 2
            if self._items[parent] <= item:
                break
            self._items[index] = self._items[parent]
            index = parent
        self._items[index] = item

    def peek_min(self) -> HeapEntry:
        if not self._items:
            raise IndexError("peek from empty MinHeap")
        return self._items[0]

    def pop_min(self) -> HeapEntry:
        if not self._items:
            raise IndexError("pop from empty MinHeap")

        minimum = self._items[0]
        last_item = self._items.pop()
        if self._items:
            index = 0
            size = len(self._items)
            while True:
                left = 2 * index + 1
                if left >= size:
                    break
                right = left + 1
                smaller_child = right if (
                    right < size and self._items[right] < self._items[left]
                ) else left
                if self._items[smaller_child] >= last_item:
                    break
                self._items[index] = self._items[smaller_child]
                index = smaller_child
            self._items[index] = last_item
        return minimum
