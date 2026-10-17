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


# ------- Step 3: Dispatcher business-flow tests (need Nhi/Duy modules) -------

from core.dispatcher import Dispatcher
from core.road_graph import RoadGraph
from core.strategies import MatchResult, MatchStrategy, DijkstraPerDriver, ReverseDijkstra
from models import ASSIGNED, BUSY, COMPLETED, FREE, QUEUED
from models.driver import Driver
from models.location import Location


class FakeStrategy(MatchStrategy):
    """Predefined strategy: tests Dispatcher without depending on A1/A2."""
    name = 'fake'

    def __init__(self, driver_id='D1', eta=2.0):
        self._driver_id = driver_id
        self._eta = eta
        self.calls = []

    def find_driver(self, graph, pickup_node, free_drivers):
        self.calls.append((pickup_node, dict(free_drivers)))
        return MatchResult(self._driver_id, self._eta, 1, ['N1', pickup_node], 0.1)


@pytest.fixture
def graph_for_dispatcher():
    graph = RoadGraph()
    graph.add_edge('N1', 'N2', 2)
    graph.add_edge('N2', 'N3', 1)
    graph.add_edge('N3', 'N4', 4)
    graph.add_edge('N4', 'N3', 3)
    graph.add_node('N5')
    return graph


def test_dispatcher_queue_ids_and_validate_nodes(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {})
    r1 = dispatcher.submit_request('N2', 'N3')
    r2 = dispatcher.submit_request('N3', 'N4')
    assert (r1.id, r2.id) == ('R1', 'R2')
    assert (r1.status, r2.status) == (QUEUED, QUEUED)
    assert [r.id for r in dispatcher.queue_snapshot()] == ['R1', 'R2']
    assert list(dispatcher.all_requests) == ['R1', 'R2']
    with pytest.raises(ValueError):
        dispatcher.submit_request('NONE', 'N3')
    with pytest.raises(ValueError):
        dispatcher.submit_request('N2', 'NONE')
    with pytest.raises(ValueError):
        dispatcher.submit_request('N2', 'N2')
    assert list(dispatcher.all_requests) == ['R1', 'R2']


def test_dispatcher_add_update_remove_driver(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {})
    d1 = dispatcher.add_driver('An', 'N1')
    d2 = dispatcher.add_driver('Binh', 'N2')
    assert (d1.id, d2.id) == ('D1', 'D2')
    assert dispatcher.update_driver('D1', name='An Moi', node='N3') is d1
    assert (d1.name, d1.node) == ('An Moi', 'N3')
    with pytest.raises(ValueError):
        dispatcher.add_driver('X', 'UNKNOWN')
    with pytest.raises(ValueError):
        dispatcher.update_driver('D1', name=' ')
    with pytest.raises(ValueError):
        dispatcher.update_driver('D1', node='UNKNOWN')
    assert dispatcher.remove_driver('D2') is True
    assert dispatcher.remove_driver('D2') is False
    assert d1.node == 'N3'


def test_dispatcher_accepts_existing_objects_without_mutating_input_containers(graph_for_dispatcher):
    initial_drivers = {'D7': Driver('D7', 'Seven', 'N1')}
    initial_trips = []
    dispatcher = Dispatcher(graph_for_dispatcher, initial_drivers, initial_trips)
    dispatcher.add_driver('Eight', 'N2')
    assert list(initial_drivers) == ['D7']
    assert initial_trips == []
    assert 'D8' in dispatcher.drivers


def test_dispatch_success_with_fake_strategy(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {})
    dispatcher.add_driver('An', 'N1')
    dispatcher.add_driver('Binh', 'N2')
    request = dispatcher.submit_request('N3', 'N4')
    fake = FakeStrategy('D2', eta=1.0)
    trip = dispatcher.dispatch_next(fake)
    assert trip is not None
    assert (trip.id, trip.driver_id, trip.request_id, trip.eta) == ('T1', 'D2', request.id, 1.0)
    assert trip.status == ASSIGNED
    assert request.status == ASSIGNED
    assert dispatcher.drivers['D2'].status == BUSY
    assert dispatcher.drivers['D1'].status == FREE
    assert len(dispatcher.queue) == 0
    assert [r.id for r in dispatcher.export_state()['requests']] == ['R1']
    assert fake.calls == [('N3', {'D1': 'N1', 'D2': 'N2'})]
    assert dispatcher.last_match_result.visited_count == 1
    assert dispatcher.can_undo() is True


def test_dispatch_no_request_returns_none(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    fake = FakeStrategy()
    assert dispatcher.dispatch_next(fake) is None
    assert fake.calls == []


def test_dispatch_without_free_driver_keeps_queue(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1', BUSY)})
    req = dispatcher.submit_request('N3', 'N4')
    fake = FakeStrategy()
    assert dispatcher.dispatch_next(fake) is None
    assert fake.calls == []
    assert dispatcher.queue.peek() is req
    assert req.status == QUEUED
    assert dispatcher.trips == []


def test_dispatch_unreachable_keeps_request_and_driver(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N5')})
    req = dispatcher.submit_request('N3', 'N4')
    assert dispatcher.dispatch_next(DijkstraPerDriver()) is None
    assert dispatcher.queue.peek() is req
    assert dispatcher.drivers['D1'].status == FREE
    assert dispatcher.trips == []


def test_dispatch_invalid_strategy_result_is_atomic(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    req = dispatcher.submit_request('N3', 'N4')
    with pytest.raises(ValueError):
        dispatcher.dispatch_next(FakeStrategy('D999', 1))
    with pytest.raises(ValueError):
        dispatcher.dispatch_next(FakeStrategy('D1', -1))
    assert dispatcher.queue.peek() is req
    assert dispatcher.drivers['D1'].status == FREE
    assert dispatcher.trips == []
    assert dispatcher.can_undo() is False


def test_dispatch_eta_zero_is_success(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N3')})
    dispatcher.submit_request('N3', 'N4')
    trip = dispatcher.dispatch_next(FakeStrategy('D1', 0.0))
    assert trip is not None and trip.eta == 0.0


def test_complete_trip_frees_driver_at_dropoff(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    trip = dispatcher.dispatch_next(FakeStrategy())
    assert dispatcher.complete_trip(trip.id) is True
    assert trip.status == COMPLETED
    assert dispatcher.drivers['D1'].status == FREE
    assert dispatcher.drivers['D1'].node == 'N4'
    assert dispatcher.complete_trip(trip.id) is False
    assert dispatcher.complete_trip('T999') is False
    assert dispatcher.can_undo() is False
    assert dispatcher.undo() is False


def test_busy_driver_cannot_be_removed(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    dispatcher.dispatch_next(FakeStrategy())
    with pytest.raises(ValueError):
        dispatcher.remove_driver('D1')


def test_undo_redo_restore_queue_driver_trip(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    r1 = dispatcher.submit_request('N3', 'N4')
    r2 = dispatcher.submit_request('N2', 'N4')
    trip = dispatcher.dispatch_next(FakeStrategy())
    assert [r.id for r in dispatcher.queue] == [r2.id]
    assert dispatcher.undo() is True
    assert [r.id for r in dispatcher.queue] == [r1.id, r2.id]
    assert r1.status == QUEUED
    assert dispatcher.drivers['D1'].status == FREE
    assert dispatcher.drivers['D1'].node == 'N1'
    assert dispatcher.trips == []
    assert dispatcher.can_redo() is True
    assert dispatcher.redo() is True
    assert [r.id for r in dispatcher.queue] == [r2.id]
    assert r1.status == ASSIGNED
    assert dispatcher.trips[0] is trip
    assert dispatcher.drivers['D1'].status == BUSY
    assert dispatcher.can_redo() is False


def test_undo_redo_multiple_actions_lifo(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {
        'D1': Driver('D1', 'An', 'N1'),
        'D2': Driver('D2', 'Binh', 'N2'),
    })
    dispatcher.submit_request('N3', 'N4')
    dispatcher.submit_request('N2', 'N4')
    t1 = dispatcher.dispatch_next(FakeStrategy('D1'))
    t2 = dispatcher.dispatch_next(FakeStrategy('D2'))
    assert [t.id for t in dispatcher.trips] == ['T1', 'T2']
    assert dispatcher.undo() is True
    assert [t.id for t in dispatcher.trips] == ['T1']
    assert dispatcher.undo() is True
    assert dispatcher.trips == []
    assert [r.id for r in dispatcher.queue] == ['R1', 'R2']
    assert dispatcher.undo() is False
    assert dispatcher.redo() is True
    assert dispatcher.trips[0] is t1
    assert dispatcher.redo() is True
    assert dispatcher.trips[1] is t2
    assert dispatcher.redo() is False


def test_new_dispatch_invalidates_redo_and_does_not_reuse_trip_id(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {
        'D1': Driver('D1', 'An', 'N1'),
        'D2': Driver('D2', 'Binh', 'N2'),
    })
    dispatcher.submit_request('N3', 'N4')
    dispatcher.dispatch_next(FakeStrategy('D1'))
    dispatcher.undo()
    assert dispatcher.can_redo()
    trip2 = dispatcher.dispatch_next(FakeStrategy('D2'))
    assert trip2.id == 'T2'
    assert dispatcher.can_redo() is False


def test_redo_rejects_changed_head_without_losing_history(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    dispatcher.dispatch_next(FakeStrategy())
    dispatcher.undo()
    dispatcher.submit_request('N2', 'N4')
    dispatcher.queue.requeue_head(dispatcher.all_requests['R2'])
    assert dispatcher.can_redo() is False
    assert dispatcher.redo() is False
    assert len(dispatcher.undo_manager.redo_stack) == 1


def test_snapshot_is_independent_copy(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    dispatcher.queue_snapshot()[0].status = ASSIGNED
    dispatcher.drivers_snapshot()['D1'].name = 'Tampered'
    assert dispatcher.all_requests['R1'].status == QUEUED
    assert dispatcher.drivers['D1'].name == 'An'
    dispatcher.dispatch_next(FakeStrategy())
    dispatcher.trips_snapshot()[0].status = COMPLETED
    assert dispatcher.trips[0].status == ASSIGNED


def test_from_state_restores_queued_requests_locations_and_next_ids(graph_for_dispatcher):
    req1 = RideRequest('R8', 'N3', 'N4', ASSIGNED)
    req2 = RideRequest('R9', 'N2', 'N4', QUEUED)
    state = {
        'graph': graph_for_dispatcher,
        'drivers': {'D7': Driver('D7', 'Seven', 'N1')},
        'requests': [req2, req1],
        'trips': [Trip('T11', 'R8', 'D7', 3.0)],
        'locations': {'N3': Location('N3', 'Point 3')},
    }
    dispatcher = Dispatcher.from_state(state)
    assert [r.id for r in dispatcher.queue] == ['R9']
    assert dispatcher.locations['N3'].name == 'Point 3'
    assert dispatcher.add_driver('Eight', 'N2').id == 'D8'
    assert dispatcher.submit_request('N3', 'N4').id == 'R10'
    assert dispatcher.dispatch_next(FakeStrategy('D8')).id == 'T12'


def test_export_import_retains_undo_queue_order(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    dispatcher.submit_request('N2', 'N4')
    dispatcher.dispatch_next(FakeStrategy())
    assert dispatcher.undo()
    state = dispatcher.export_state()
    restored = Dispatcher.from_state(state)
    assert [r.id for r in restored.queue] == ['R1', 'R2']
    assert restored.undo() is False  # Undo history is kept in UI session, not saved in JSON.
    assert [r.id for r in restored.export_state()['requests']] == ['R1', 'R2']


@pytest.mark.parametrize('strategy_cls', [DijkstraPerDriver, ReverseDijkstra])
def test_end_to_end_with_real_a1_a2(graph_for_dispatcher, strategy_cls):
    dispatcher = Dispatcher(graph_for_dispatcher, {
        'D1': Driver('D1', 'An', 'N1'),
        'D2': Driver('D2', 'Binh', 'N2'),
    })
    dispatcher.submit_request('N3', 'N4')
    trip = dispatcher.dispatch_next(strategy_cls())
    assert trip.driver_id == 'D2'  # N2 -> N3 has ETA=1, N1 -> N3 has ETA=3.
    assert trip.eta == 1.0
    assert dispatcher.complete_trip(trip.id) is True
    assert dispatcher.drivers['D2'].node == 'N4'
    assert dispatcher.drivers['D2'].status == FREE


def test_remove_driver_referenced_by_completed_trip_is_rejected(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    trip = dispatcher.dispatch_next(FakeStrategy())
    dispatcher.complete_trip(trip.id)
    with pytest.raises(ValueError):
        dispatcher.remove_driver('D1')


def test_submit_rejects_unreachable_dropoff(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {})
    with pytest.raises(ValueError):
        d.submit_request('N1', 'N5')  # N5 cô lập
    assert d.all_requests == {}


def test_failure_reasons(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N5')})
    assert d.dispatch_next(DijkstraPerDriver()) is None and d.last_failure == 'empty_queue'
    d.submit_request('N3', 'N4')
    assert d.dispatch_next(DijkstraPerDriver()) is None and d.last_failure == 'no_route'
    d.drivers['D1'].status = BUSY
    assert d.dispatch_next(DijkstraPerDriver()) is None and d.last_failure == 'no_free_driver'


def test_dispatch_all_and_stepwise_undo(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1'),
                                          'D2': Driver('D2', 'Binh', 'N2')})
    d.submit_request('N3', 'N4')
    d.submit_request('N2', 'N4')
    assert len(d.dispatch_all(ReverseDijkstra())) == 2
    assert d.last_failure == 'empty_queue'
    assert d.undo() and d.undo() and not d.can_undo()


def test_complete_trip_clears_history_and_busy_driver_cannot_move(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    d.submit_request('N3', 'N4')
    d.submit_request('N2', 'N4')
    t1 = d.dispatch_next(FakeStrategy('D1'))
    with pytest.raises(ValueError):
        d.update_driver('D1', node='N2')
    d.complete_trip(t1.id)
    assert not d.can_undo() and not d.can_redo()

