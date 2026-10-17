import pytest

from core.structures import RequestQueue, Stack
from models.ride_request import RideRequest


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
