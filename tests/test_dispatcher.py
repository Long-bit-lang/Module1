import pytest

from core.structures import RequestQueue, Stack
from core.undo_manager import DispatchAction, UndoManager
from models.ride_request import RideRequest
from models.trip import Trip


def request(id):
    return RideRequest(id, "N1", "N2")


def test_queue_fifo_and_requeue_head():
    q = RequestQueue()
    r1, r2, r3 = request("R1"), request("R2"), request("R3")
    assert q.peek() is None
    q.enqueue(r1)
    q.enqueue(r2)
    assert q.peek() is r1
    assert len(q) == 2
    assert q.dequeue() is r1
    q.requeue_head(r3)
    assert [r.id for r in q] == ["R3", "R2"]
    assert q.dequeue() is r3
    assert q.dequeue() is r2
    assert q.peek() is None
    assert len(q) == 0
    with pytest.raises(IndexError):
        q.dequeue()
    q.enqueue(r1)
    assert q.dequeue() is r1


def test_stack_lifo_and_clear():
    s = Stack()
    s.push(1)
    s.push(2)
    assert len(s) == 2
    assert s.pop() == 2
    assert s.pop() == 1
    with pytest.raises(IndexError):
        s.pop()
    s.push(3)
    s.clear()
    assert len(s) == 0


# ------- Step 2: UndoManager tests (does not mutate domain objects) -------

def _dispatch_action(number: int) -> DispatchAction:
    req = request(f"R{number}")
    trip = Trip(f"T{number}", req.id, "D1", 3.5)
    return DispatchAction(trip, "D1", req, previous_driver_node="N1")


def test_undo_manager_empty_history():
    manager = UndoManager()
    assert len(manager.undo_stack) == 0
    assert len(manager.redo_stack) == 0
    assert manager.undo() is None
    assert manager.redo() is None


def test_undo_manager_record_and_undo_once():
    manager = UndoManager()
    action = _dispatch_action(1)
    manager.record(action)
    assert len(manager.undo_stack) == 1
    assert manager.undo() is action
    assert len(manager.undo_stack) == 0
    assert len(manager.redo_stack) == 1
    assert manager.undo() is None


def test_undo_manager_redo_once():
    manager = UndoManager()
    action = _dispatch_action(1)
    manager.record(action)
    manager.undo()
    assert manager.redo() is action
    assert len(manager.undo_stack) == 1
    assert len(manager.redo_stack) == 0
    assert manager.redo() is None


def test_undo_manager_lifo_multiple_actions():
    manager = UndoManager()
    first = _dispatch_action(1)
    second = _dispatch_action(2)
    manager.record(first)
    manager.record(second)
    assert manager.undo() is second
    assert manager.undo() is first
    assert manager.redo() is first
    assert manager.redo() is second
    assert len(manager.undo_stack) == 2
    assert len(manager.redo_stack) == 0


def test_new_record_clears_redo_history():
    manager = UndoManager()
    first = _dispatch_action(1)
    second = _dispatch_action(2)
    manager.record(first)
    manager.undo()
    assert len(manager.redo_stack) == 1
    manager.record(second)
    assert len(manager.redo_stack) == 0
    assert manager.redo() is None
    assert manager.undo() is second


def test_dispatch_action_retains_previous_driver_node():
    action = _dispatch_action(1)
    assert action.driver_id == "D1"
    assert action.request.id == "R1"
    assert action.trip.id == "T1"
    assert action.previous_driver_node == "N1"
