"""History of dispatch actions using the custom LIFO Stack.

UndoManager ONLY moves DispatchAction records between two stacks.
Dispatcher (implemented in the next step) changes trips, drivers and the queue.
"""
from __future__ import annotations

from dataclasses import dataclass

from models.ride_request import RideRequest
from models.trip import Trip
from .structures import Stack


@dataclass
class DispatchAction:
    trip: Trip
    driver_id: str
    request: RideRequest
    previous_driver_node: str | None = None


class UndoManager:
    def __init__(self) -> None:
        self.undo_stack = Stack()
        self.redo_stack = Stack()

    def record(self, action: DispatchAction) -> None:
        """Save a new dispatch and invalidate the redo history."""
        self.undo_stack.push(action)
        self.redo_stack.clear()

    def undo(self) -> DispatchAction | None:
        """Move the latest action to redo history; return None if empty."""
        if len(self.undo_stack) == 0:
            return None
        action = self.undo_stack.pop()
        self.redo_stack.push(action)
        return action

    def redo(self) -> DispatchAction | None:
        """Move the latest undone action back to undo history."""
        if len(self.redo_stack) == 0:
            return None
        action = self.redo_stack.pop()
        self.undo_stack.push(action)
        return action
