"""TV5 - Kiểm tra chữ ký API thật có khớp docs/CONTRACT.md hay chưa."""
import importlib
import inspect

import pytest

EXPECTED = {
    "core.road_graph:RoadGraph": [
        "add_node",
        "has_node",
        "add_edge",
        "nodes",
        "edges",
        "neighbors",
        "reversed",
    ],
    "core.structures:RequestQueue": ["enqueue", "dequeue", "peek", "requeue_head", "remove", "__len__"],
    "core.structures:Stack": ["push", "pop", "peek", "clear", "__len__"],
    "core.undo_manager:UndoManager": ["record", "undo", "redo"],
    "core.dispatcher:Dispatcher": [
        "submit_request",
        "add_driver",
        "update_driver",
        "remove_driver",
        "dispatch_next",
        "dispatch_all",
        "cancel_request",
        "ride_estimate",
        "complete_trip",
        "can_undo",
        "can_redo",
        "undo",
        "redo",
        "queue_snapshot",
        "trips_snapshot",
        "drivers_snapshot",
        "from_state",
        "export_state",
    ],
    "core.json_storage:JsonStorage": ["load_all", "save_all"],
    "models.driver:Driver": ["assign", "release", "to_dict", "from_dict"],
}


def _load(path):
    module, cls = path.split(":")
    return getattr(importlib.import_module(module), cls)


@pytest.mark.parametrize("path", EXPECTED)
def test_class_has_contract_methods(path):
    cls = _load(path)
    missing = [m for m in EXPECTED[path] if not hasattr(cls, m)]
    assert not missing, f"{path} thiếu: {missing}"


def test_submit_request_signature():
    from core.dispatcher import Dispatcher

    params = list(inspect.signature(Dispatcher.submit_request).parameters)
    assert params == ["self", "pickup_node", "dropoff_node"]


def test_dispatcher_accepts_all_requests():
    from core.dispatcher import Dispatcher

    assert "all_requests" in inspect.signature(Dispatcher.__init__).parameters


def test_dispatcher_accepts_locations():
    from core.dispatcher import Dispatcher

    assert "locations" in inspect.signature(Dispatcher.__init__).parameters


def test_strategies_registry():
    from core.strategies import STRATEGIES

    assert set(STRATEGIES) == {"A1 - Dijkstra từng tài xế", "A2 - Dijkstra đảo chiều"}


def test_models_export_status_constants():
    import models

    for name in ("FREE", "BUSY", "QUEUED", "ASSIGNED", "COMPLETED"):
        assert hasattr(models, name), name


def test_ride_request_has_status():
    from models.ride_request import RideRequest

    assert RideRequest("R1", "N1", "N2").status == "queued"


def test_dispatch_action_dataclass():
    from core.undo_manager import DispatchAction

    assert {"trip", "driver_id", "request"} <= set(DispatchAction.__dataclass_fields__)


def test_last_failure_values_are_lowercase():
    """Mã lý do thất bại dùng chữ thường, khớp CONTRACT §5 và tab_dispatch._REASON."""
    from core.dispatcher import EMPTY_QUEUE, NO_FREE_DRIVER, NO_ROUTE

    assert EMPTY_QUEUE == "empty_queue"
    assert NO_FREE_DRIVER == "no_free_driver"
    assert NO_ROUTE == "no_route"


def test_dispatch_next_sets_last_failure_empty_queue():
    """dispatch_next với hàng đợi rỗng gán last_failure = 'empty_queue'."""
    from core.dispatcher import Dispatcher
    from core.road_graph import RoadGraph
    from core.strategies import DijkstraPerDriver
    from models.driver import Driver

    g = RoadGraph()
    g.add_node("N1")
    g.add_node("N2")
    g.add_edge("N1", "N2", 1)
    d = Dispatcher(g, {"D1": Driver("D1", "Tài xế", "N1")})
    result = d.dispatch_next(DijkstraPerDriver())
    assert result is None
    assert d.last_failure == "empty_queue"


def test_dispatch_next_sets_last_failure_no_free_driver():
    """dispatch_next khi không có tài xế rảnh gán last_failure = 'no_free_driver'."""
    from core.dispatcher import Dispatcher
    from core.road_graph import RoadGraph
    from core.strategies import DijkstraPerDriver
    from models import BUSY
    from models.driver import Driver

    g = RoadGraph()
    g.add_node("N1")
    g.add_node("N2")
    g.add_edge("N1", "N2", 1)
    driver = Driver("D1", "Tài xế", "N1")
    driver.assign()  # status = BUSY
    d = Dispatcher(g, {"D1": driver})
    d.submit_request("N1", "N2")
    result = d.dispatch_next(DijkstraPerDriver())
    assert result is None
    assert d.last_failure == "no_free_driver"
