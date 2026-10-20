import pytest

from core.structures import RequestQueue, Stack
from models.ride_request import RideRequest
from models.trip import Trip


def request(id):
    return RideRequest(id, "N1", "N2")


def test_queue_fifo():
    q = RequestQueue()
    r1, r2 = request("R1"), request("R2")
    assert q.peek() is None
    q.enqueue(r1)
    q.enqueue(r2)
    assert q.peek() is r1
    assert len(q) == 2
    assert q.dequeue() is r1
    assert q.dequeue() is r2
    assert q.peek() is None
    assert len(q) == 0
    with pytest.raises(IndexError):
        q.dequeue()
    q.enqueue(r1)
    assert q.dequeue() is r1


def test_request_queue_remove_operations():
    # 1. Xóa phần tử duy nhất (single item queue)
    q1 = RequestQueue()
    r1 = request("R1")
    q1.enqueue(r1)
    assert len(q1) == 1
    assert q1.remove("R1") is True
    assert len(q1) == 0
    assert q1.peek() is None
    assert q1._head is None
    assert q1._tail is None
    # Sau khi xóa về rỗng, enqueue lại phải hoạt động bình thường
    r_new = request("R_new")
    q1.enqueue(r_new)
    assert len(q1) == 1
    assert q1.peek() is r_new
    assert q1._tail.value is r_new
    assert q1.dequeue() is r_new

    # 2. Xóa đầu (head) trong hàng đợi nhiều phần tử
    q2 = RequestQueue()
    ra, rb, rc = request("RA"), request("RB"), request("RC")
    q2.enqueue(ra)
    q2.enqueue(rb)
    q2.enqueue(rc)
    assert q2.remove("RA") is True
    assert len(q2) == 2
    assert [r.id for r in q2] == ["RB", "RC"]
    assert q2.peek() is rb
    assert q2._head.value is rb
    assert q2._tail.value is rc

    # 3. Xóa giữa (middle)
    q3 = RequestQueue()
    q3.enqueue(ra)
    q3.enqueue(rb)
    q3.enqueue(rc)
    assert q3.remove("RB") is True
    assert len(q3) == 2
    assert [r.id for r in q3] == ["RA", "RC"]
    assert q3._head.value is ra
    assert q3._tail.value is rc

    # 4. Xóa cuối (tail) và kiểm tra con trỏ _tail được cập nhật về node liền trước
    q4 = RequestQueue()
    q4.enqueue(ra)
    q4.enqueue(rb)
    q4.enqueue(rc)
    assert q4.remove("RC") is True
    assert len(q4) == 2
    assert [r.id for r in q4] == ["RA", "RB"]
    assert q4._head.value is ra
    assert q4._tail.value is rb
    # Sau khi xóa tail, enqueue thêm phần tử mới phải nối tiếp vào tail mới (RB)
    rd = request("RD")
    q4.enqueue(rd)
    assert len(q4) == 3
    assert [r.id for r in q4] == ["RA", "RB", "RD"]
    assert q4._tail.value is rd
    assert q4.dequeue() is ra
    assert q4.dequeue() is rb
    assert q4.dequeue() is rd

    # 5. Xóa ID không tồn tại
    assert q3.remove("NON_EXISTENT") is False
    assert len(q3) == 2
    assert q4.remove("NON_EXISTENT") is False
    assert len(q4) == 0


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


# ------- Step 3: Dispatcher business-flow tests (need Nhi/Duy modules) -------

from core.dispatcher import Dispatcher
from core.road_graph import RoadGraph
from core.strategies import MatchResult, MatchStrategy, DijkstraPerDriver, ReverseDijkstra
from models import ASSIGNED, BUSY, CANCELLED, COMPLETED, FREE, QUEUED
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


def test_busy_driver_cannot_be_removed(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    dispatcher.dispatch_next(FakeStrategy())
    with pytest.raises(ValueError):
        dispatcher.remove_driver('D1')


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


def test_dispatch_all(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1'),
                                          'D2': Driver('D2', 'Binh', 'N2')})
    d.submit_request('N3', 'N4')
    d.submit_request('N2', 'N4')
    assert len(d.dispatch_all(ReverseDijkstra())) == 2
    assert d.last_failure == 'empty_queue'


def test_busy_driver_cannot_move(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    d.submit_request('N3', 'N4')
    d.submit_request('N2', 'N4')
    t1 = d.dispatch_next(FakeStrategy('D1'))
    with pytest.raises(ValueError):
        d.update_driver('D1', node='N2')
    d.complete_trip(t1.id)
    assert d.drivers['D1'].status == FREE


def test_dispatcher_cancel_request(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {"D1": Driver("D1", "An", "N1")})
    r1 = d.submit_request("N3", "N4")
    r2 = d.submit_request("N2", "N4")
    assert len(d.queue) == 2
    assert r1.id in d.all_requests

    # Hủy yêu cầu đang chờ hợp lệ
    assert d.cancel_request(r1.id) is True
    assert len(d.queue) == 1
    assert r1.id not in d.all_requests
    assert [r.id for r in d.queue] == [r2.id]

    # Hủy ID không tồn tại
    assert d.cancel_request("NON_EXISTENT") is False

    # Hủy yêu cầu đã được điều phối (ASSIGNED) -> phải trả về False
    trip = d.dispatch_next(FakeStrategy("D1"))
    assert trip is not None
    assert r2.status == ASSIGNED
    assert d.cancel_request(r2.id) is False


def test_dispatcher_ride_estimate(graph_for_dispatcher):
    d = Dispatcher(graph_for_dispatcher, {})
    req = d.submit_request("N1", "N4")

    # Cách gọi 1: theo request_id đã có
    est1 = d.ride_estimate(req.id)
    assert est1 is not None
    distance, path = est1
    assert distance == 7.0
    assert path == ["N1", "N2", "N3", "N4"]

    # Cách gọi 2: theo cặp (pickup_node, dropoff_node) trực tiếp
    est2 = d.ride_estimate("N1", "N4")
    assert est2 == est1

    # Yêu cầu không tồn tại
    assert d.ride_estimate("NON_EXISTENT_REQ") is None

    # Điểm không có đường đi (đến đỉnh cô lập N5)
    assert d.ride_estimate("N1", "N5") is None


# ------- cancel_trip tests -------

def test_cancel_trip_success(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    req = dispatcher.submit_request('N3', 'N4')
    trip = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert trip is not None
    assert trip.status == ASSIGNED
    assert dispatcher.drivers['D1'].status == BUSY
    assert req.status == ASSIGNED
    assert len(dispatcher.queue) == 0

    assert dispatcher.cancel_trip(trip.id) is True
    assert trip.status == CANCELLED
    assert dispatcher.drivers['D1'].status == FREE
    assert dispatcher.drivers['D1'].node == 'N1'  # Giữ nguyên vị trí cũ của tài xế
    assert req.status == CANCELLED
    assert len(dispatcher.queue) == 0  # D1 = A: không quay lại hàng đợi
    assert req.id in dispatcher.all_requests
    assert dispatcher.all_requests[req.id].status == CANCELLED


def test_cancel_trip_invalid_status_or_id(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    # Hủy trip không tồn tại
    assert dispatcher.cancel_trip('NON_EXISTENT') is False

    req1 = dispatcher.submit_request('N3', 'N4')
    t1 = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert dispatcher.complete_trip(t1.id) is True
    assert t1.status == COMPLETED

    # Hủy trip đã COMPLETED -> trả False và không đổi dữ liệu
    assert dispatcher.cancel_trip(t1.id) is False
    assert t1.status == COMPLETED
    assert dispatcher.drivers['D1'].node == 'N4'

    # Ghép chuyến khác và hủy thành công
    req2 = dispatcher.submit_request('N3', 'N4')
    t2 = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert dispatcher.cancel_trip(t2.id) is True
    assert t2.status == CANCELLED

    # Hủy lại trip đã CANCELLED -> trả False và không đổi gì
    assert dispatcher.cancel_trip(t2.id) is False
    assert t2.status == CANCELLED


def test_complete_trip_on_cancelled_trip_returns_false(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    t1 = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert dispatcher.cancel_trip(t1.id) is True
    assert t1.status == CANCELLED

    # Gọi complete_trip trên chuyến CANCELLED phải trả False
    assert dispatcher.complete_trip(t1.id) is False
    assert t1.status == CANCELLED
    assert dispatcher.drivers['D1'].status == FREE
    assert dispatcher.drivers['D1'].node == 'N1'


def test_cancelled_driver_can_take_new_trip_without_id_clash(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    t1 = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert t1.id == 'T1'
    assert dispatcher.cancel_trip(t1.id) is True

    # Tài xế D1 đã FREE, gửi yêu cầu mới và ghép chuyến
    r2 = dispatcher.submit_request('N2', 'N4')
    t2 = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert t2 is not None
    assert t2.id == 'T2'  # ID mới tăng dần, không trùng T1
    assert t2.driver_id == 'D1'
    assert t2.request_id == r2.id
    assert t2.status == ASSIGNED
    assert dispatcher.drivers['D1'].status == BUSY


def test_remove_driver_blocked_for_driver_with_cancelled_trip(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    dispatcher.submit_request('N3', 'N4')
    t1 = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert dispatcher.cancel_trip(t1.id) is True
    assert dispatcher.drivers['D1'].status == FREE

    # remove_driver vẫn bị chặn với tài xế có chuyến CANCELLED
    with pytest.raises(ValueError):
        dispatcher.remove_driver('D1')


def test_export_from_state_preserves_cancelled_trip_and_request(graph_for_dispatcher):
    dispatcher = Dispatcher(graph_for_dispatcher, {'D1': Driver('D1', 'An', 'N1')})
    r1 = dispatcher.submit_request('N3', 'N4')
    t1 = dispatcher.dispatch_next(FakeStrategy('D1'))
    assert dispatcher.cancel_trip(t1.id) is True

    r2 = dispatcher.submit_request('N2', 'N4')  # Vẫn QUEUED
    state = dispatcher.export_state()

    assert any(t.id == 'T1' and t.status == CANCELLED for t in state['trips'])
    assert any(r.id == 'R1' and r.status == CANCELLED for r in state['requests'])
    assert any(r.id == 'R2' and r.status == QUEUED for r in state['requests'])

    restored = Dispatcher.from_state(state)
    assert [r.id for r in restored.queue] == ['R2']  # R1 CANCELLED không vào queue
    assert restored.all_requests['R1'].status == CANCELLED
    assert restored.trips[0].id == 'T1'
    assert restored.trips[0].status == CANCELLED
    assert restored.drivers['D1'].status == FREE


