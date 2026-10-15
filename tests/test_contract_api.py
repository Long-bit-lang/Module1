"""TV5 - Kiểm tra chữ ký API thật có khớp docs/CONTRACT.md hay chưa.

Mỗi mục là một xfail (không strict): khi module của thành viên nào hoàn thiện thì test tự
chuyển thành XPASS; sau đó người phụ trách gỡ dấu xfail của mục đó để nó thành test thường.
"""
import importlib
import inspect

import pytest

EXPECTED = {
    "core.road_graph:RoadGraph": ["add_node", "has_node", "add_edge", "nodes", "edges",
                                  "neighbors", "reversed"],
    "core.structures:RequestQueue": ["enqueue", "dequeue", "peek", "requeue_head", "__len__"],
    "core.structures:Stack": ["push", "pop", "clear", "__len__"],
    "core.undo_manager:UndoManager": ["record", "undo", "redo"],
    "core.dispatcher:Dispatcher": [
        "submit_request", "add_driver", "update_driver", "remove_driver", "dispatch_next",
        "complete_trip", "can_undo", "can_redo", "undo", "redo", "queue_snapshot",
        "trips_snapshot", "drivers_snapshot", "from_state", "export_state"],
    "core.json_storage:JsonStorage": ["load_all", "save_all"],
    "models.driver:Driver": ["assign", "release", "to_dict", "from_dict"],
}
XFAIL = pytest.mark.xfail(reason="Skeleton chưa theo CONTRACT", strict=False)


def _load(path):
    module, cls = path.split(":")
    return getattr(importlib.import_module(module), cls)


@XFAIL
@pytest.mark.parametrize("path", EXPECTED)
def test_class_has_contract_methods(path):
    cls = _load(path)
    missing = [m for m in EXPECTED[path] if not hasattr(cls, m)]
    assert not missing, f"{path} thiếu: {missing}"


@XFAIL
def test_submit_request_signature():
    from core.dispatcher import Dispatcher
    params = list(inspect.signature(Dispatcher.submit_request).parameters)
    assert params == ["self", "pickup_node", "dropoff_node"]


@XFAIL
def test_dispatcher_accepts_all_requests():
    from core.dispatcher import Dispatcher
    assert "all_requests" in inspect.signature(Dispatcher.__init__).parameters


@XFAIL
def test_strategies_registry():
    from core.strategies import STRATEGIES
    assert set(STRATEGIES) == {"A1 - Dijkstra từng tài xế", "A2 - Dijkstra đảo chiều"}


@XFAIL
def test_models_export_status_constants():
    import models
    for name in ("FREE", "BUSY", "QUEUED", "ASSIGNED", "COMPLETED"):
        assert hasattr(models, name), name


@XFAIL
def test_ride_request_has_status():
    from models.ride_request import RideRequest
    assert RideRequest("R1", "N1", "N2").status == "queued"


@XFAIL
def test_dispatch_action_dataclass():
    from core.undo_manager import DispatchAction
    assert {"trip", "driver_id", "request"} <= set(DispatchAction.__dataclass_fields__)
