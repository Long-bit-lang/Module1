"""Kiểm thử tích hợp đầu-cuối: JsonStorage, RoadGraph, Dispatcher, Strategies và Models."""
from __future__ import annotations

from pathlib import Path
import pytest

from core.dispatcher import Dispatcher
from core.json_storage import JsonStorage
from core.strategies import DijkstraPerDriver, ReverseDijkstra
from models import ASSIGNED, BUSY, COMPLETED, FREE


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


def test_undo_then_save_reload_preserves_queue_order_resets_undo(tmp_path: Path):
    """Undo rồi save/reload: thứ tự hàng đợi bảo toàn (R3 về đầu), lịch sử Undo không lưu xuống JSON."""
    storage = JsonStorage(runtime_dir=tmp_path)
    dispatcher = Dispatcher.from_state(storage.load_all())

    trip = dispatcher.dispatch_next(DijkstraPerDriver())
    assert trip is not None
    assert [r.id for r in dispatcher.queue] == ["R4"]

    assert dispatcher.undo() is True
    assert [r.id for r in dispatcher.queue] == ["R3", "R4"]

    storage.save_all(dispatcher.export_state())

    reloaded = Dispatcher.from_state(storage.load_all())
    assert [r.id for r in reloaded.queue] == ["R3", "R4"]
    assert reloaded.can_undo() is False  # Lịch sử Undo thuộc về phiên runtime, không lưu trong JSON


def test_complete_trip_moves_driver_and_persists(tmp_path: Path):
    """Hoàn thành chuyến giải phóng tài xế tại điểm trả khách, xóa lịch sử Undo và lưu đúng."""
    storage = JsonStorage(runtime_dir=tmp_path)
    dispatcher = Dispatcher.from_state(storage.load_all())

    trip = dispatcher.dispatch_next(DijkstraPerDriver())
    assert trip is not None
    dropoff_node = dispatcher.all_requests[trip.request_id].dropoff_node
    assert dropoff_node == "N6"

    assert dispatcher.complete_trip(trip.id) is True
    assert dispatcher.drivers[trip.driver_id].node == "N6"
    assert dispatcher.drivers[trip.driver_id].status == FREE
    assert dispatcher.can_undo() is False
    assert dispatcher.can_redo() is False

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
