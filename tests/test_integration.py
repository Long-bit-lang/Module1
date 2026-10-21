"""Kiểm thử tích hợp đầu-cuối: JsonStorage, RoadGraph, Dispatcher, Strategies và Models."""
from __future__ import annotations

from pathlib import Path
import pytest

from core.dispatcher import Dispatcher
from core.json_storage import JsonStorage
from core.strategies import DijkstraPerDriver, ReverseDijkstra
from models import ASSIGNED, BUSY, CANCELLED, COMPLETED, FREE


def test_seed_load_dispatch_save_and_reload(tmp_path: Path):
    """Nạp seed -> dispatch_next(A1) -> save_all -> load lại: chuyến và hàng đợi bảo toàn."""
    storage = JsonStorage(runtime_dir=tmp_path)
    state = storage.load_all()
    dispatcher = Dispatcher.from_state(state)

    # Ban đầu hàng đợi có R3, R4
    queue_before = [r.id for r in dispatcher.queue]
    assert queue_before == ["R3", "R4"]

    # Điều phối yêu cầu đầu tiên (R3) bằng A1
    trip = dispatcher.dispatch_next(DijkstraPerDriver())
    assert trip is not None
    assert trip.id == "T3"
    assert trip.request_id == "R3"
    assert trip.driver_id == "D1"
    assert trip.eta == 6.0

    # Lưu lại trạng thái
    storage.save_all(dispatcher.export_state())

    # Nạp lại từ đĩa và đối chiếu
    reloaded_state = storage.load_all()
    reloaded_dispatcher = Dispatcher.from_state(reloaded_state)

    assert len(reloaded_dispatcher.trips) == 3  # T1, T2 (seed) + T3
    assert [r.id for r in reloaded_dispatcher.queue] == ["R4"]
    assert reloaded_dispatcher.drivers["D1"].status == BUSY
    assert reloaded_dispatcher.all_requests["R3"].status == ASSIGNED


def test_tiebreak_eta_a1_and_a2_agree_on_seed(tmp_path: Path):
    """Hòa ETA trên seed: R3 (pickup N4) -> cả A1 và A2 đều chọn D1 vì ID nhỏ hơn D2."""
    for strategy_cls in (DijkstraPerDriver, ReverseDijkstra):
        storage = JsonStorage(runtime_dir=tmp_path / strategy_cls.__name__)
        dispatcher = Dispatcher.from_state(storage.load_all())

        trip = dispatcher.dispatch_next(strategy_cls())
        assert trip is not None
        assert trip.request_id == "R3"
        assert (trip.driver_id, trip.eta) == ("D1", 6.0)


def test_cancel_seed_t2_assigned_trip_save_and_reload(tmp_path: Path):
    """Seed -> hủy T2 (seed có T2 ASSIGNED của D3) -> save -> reload: D3 FREE, T2 CANCELLED, R2 CANCELLED, hàng đợi vẫn R3, R4."""
    storage = JsonStorage(runtime_dir=tmp_path)
    dispatcher = Dispatcher.from_state(storage.load_all())

    # Kiểm tra trạng thái seed ban đầu
    assert dispatcher.drivers["D3"].status == BUSY
    d3_node = dispatcher.drivers["D3"].node
    t2 = next(t for t in dispatcher.trips if t.id == "T2")
    assert t2.status == ASSIGNED
    assert dispatcher.all_requests["R2"].status == ASSIGNED
    assert [r.id for r in dispatcher.queue] == ["R3", "R4"]

    # Hủy chuyến T2
    assert dispatcher.cancel_trip("T2") is True
    assert t2.status == CANCELLED
    assert dispatcher.drivers["D3"].status == FREE
    assert dispatcher.drivers["D3"].node == d3_node  # Không đổi vị trí tài xế
    assert dispatcher.all_requests["R2"].status == CANCELLED
    assert [r.id for r in dispatcher.queue] == ["R3", "R4"]

    # Lưu xuống đĩa và nạp lại
    storage.save_all(dispatcher.export_state())
    reloaded = Dispatcher.from_state(storage.load_all())

    assert reloaded.drivers["D3"].status == FREE
    assert reloaded.drivers["D3"].node == d3_node
    reloaded_t2 = next(t for t in reloaded.trips if t.id == "T2")
    assert reloaded_t2.status == CANCELLED
    assert reloaded.all_requests["R2"].status == CANCELLED
    assert [r.id for r in reloaded.queue] == ["R3", "R4"]


def test_complete_trip_moves_driver_and_persists(tmp_path: Path):
    """Hoàn thành chuyến giải phóng tài xế tại điểm trả khách và lưu đúng."""
    storage = JsonStorage(runtime_dir=tmp_path)
    dispatcher = Dispatcher.from_state(storage.load_all())

    trip = dispatcher.dispatch_next(DijkstraPerDriver())
    assert trip is not None
    dropoff_node = dispatcher.all_requests[trip.request_id].dropoff_node
    assert dropoff_node == "N6"

    assert dispatcher.complete_trip(trip.id) is True
    assert dispatcher.drivers[trip.driver_id].node == "N6"
    assert dispatcher.drivers[trip.driver_id].status == FREE

    storage.save_all(dispatcher.export_state())

    reloaded = Dispatcher.from_state(storage.load_all())
    assert reloaded.drivers[trip.driver_id].node == "N6"
    assert reloaded.drivers[trip.driver_id].status == FREE
    assert reloaded.trips_snapshot()[-1].status == COMPLETED


def test_id_generation_after_reload(tmp_path: Path):
    """Sau khi tải lại dữ liệu từ đĩa, các ID mới sinh không trùng với ID đã có."""
    storage = JsonStorage(runtime_dir=tmp_path)
    dispatcher = Dispatcher.from_state(storage.load_all())
    storage.save_all(dispatcher.export_state())

    reloaded = Dispatcher.from_state(storage.load_all())
    d_new = reloaded.add_driver("Driver Four", "N1")
    assert d_new.id == "D4"

    r_new = reloaded.submit_request("N1", "N2")
    assert r_new.id == "R5"

    t_new = reloaded.dispatch_next(DijkstraPerDriver())
    assert t_new is not None
    assert t_new.id == "T3"


def test_remove_driver_with_trip_history_raises_error(tmp_path: Path):
    """Tài xế đã có lịch sử chuyến (D1 trong T1, D3 trong T2) không thể bị xóa."""
    storage = JsonStorage(runtime_dir=tmp_path)
    dispatcher = Dispatcher.from_state(storage.load_all())

    with pytest.raises(ValueError):
        dispatcher.remove_driver("D1")

    with pytest.raises(ValueError):
        dispatcher.remove_driver("D3")


def test_seed_dispatch_complete_save_reload_trip_route_two_legs(tmp_path: Path):
    """Kịch bản: seed -> dispatch R3 bằng A1 -> complete -> save -> reload:
    - trip_route(T3) có pickup_path kết thúc ở N4 và ride_path nối N4 -> N6
    - trip_route('T1') (seed COMPLETED) có pickup_known=False
    - trip_route('T2') (seed ASSIGNED) có pickup_known=True suy ra từ vị trí tài xế
    """
    storage = JsonStorage(runtime_dir=tmp_path)
    dispatcher = Dispatcher.from_state(storage.load_all())

    # 1. Điều phối R3 bằng A1
    t3 = dispatcher.dispatch_next(DijkstraPerDriver())
    assert t3 is not None
    assert t3.id == "T3"
    assert t3.request_id == "R3"

    # 2. Hoàn thành chuyến T3
    assert dispatcher.complete_trip("T3") is True

    # 3. Lưu và nạp lại từ runtime
    storage.save_all(dispatcher.export_state())
    reloaded = Dispatcher.from_state(storage.load_all())

    # 4. Kiểm tra trip_route(T3) sau khi nạp lại
    route_t3 = reloaded.trip_route("T3")
    assert route_t3 is not None
    assert route_t3["pickup_known"] is True
    assert len(route_t3["pickup_path"]) >= 2
    assert route_t3["pickup_path"][-1] == "N4"
    assert route_t3["ride_path"][0] == "N4"
    assert route_t3["ride_path"][-1] == "N6"
    assert route_t3["pickup_eta"] == 6.0
    assert route_t3["ride_eta"] is not None

    # 5. Kiểm tra trip_route('T1') (seed đã hoàn thành, không lưu pickup_path ban đầu)
    route_t1 = reloaded.trip_route("T1")
    assert route_t1 is not None
    assert route_t1["pickup_known"] is False
    assert route_t1["pickup_path"] == []
    assert len(route_t1["ride_path"]) >= 2

    # 6. Kiểm tra trip_route('T2') (seed ASSIGNED, suy ra từ vị trí tài xế)
    route_t2 = reloaded.trip_route("T2")
    assert route_t2 is not None
    assert route_t2["pickup_known"] is True
    assert len(route_t2["pickup_path"]) >= 2
    assert route_t2["pickup_path"][-1] == reloaded.all_requests["R2"].pickup_node
