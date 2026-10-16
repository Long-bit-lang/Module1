from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from src.core.json_storage import JsonStorage, StorageError
from src.core.road_graph import RoadGraph
from src.models.driver import BUSY, FREE, Driver
from src.models.location import Location
from src.models.ride_request import RideRequest
from src.models.trip import Trip

#Tạm thời cho đến khi các trạng thái này được set trong thư viện chính
ASSIGNED = 'assigned'
QUEUED = 'QUEUED'
COMPLETED = 'COMPLETED'

def _write_json(path: Path, data: dict | list) -> None:
    """Hàm phụ trợ ghi nhanh dữ liệu JSON vào file trong thư mục tạm."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@pytest.fixture
def valid_seed_data() -> dict[str, dict]:
    """Bộ dữ liệu mẫu hợp lệ tuân thủ đúng schema trong CONTRACT.md."""
    return {
        "graph.json": {
            "nodes": [
                {"id": "N1", "name": "Đại học Bách Khoa"},
                {"id": "N2", "name": "Bến xe Trung tâm"},
                {"id": "N3", "name": "Cầu Rồng"},
            ],
            "edges": [
                {"from": "N1", "to": "N2", "weight": 4.0},
                {"from": "N2", "to": "N3", "weight": 6.5},
            ],
        },
        "drivers.json": {
            "drivers": [
                {"id": "D1", "name": "Nguyễn Văn An", "node": "N1", "status": FREE},
                {"id": "D2", "name": "Trần Văn Bình", "node": "N2", "status": BUSY},
            ]
        },
        "requests.json": {
            "requests": [
                {"id": "R1", "pickup_node": "N1", "dropoff_node": "N2", "status": ASSIGNED},
                {"id": "R2", "pickup_node": "N2", "dropoff_node": "N3", "status": QUEUED},
            ]
        },
        "trips.json": {
            "trips": [
                {"id": "T1", "request_id": "R1", "driver_id": "D2", "eta": 4.0, "status": ASSIGNED},
            ]
        },
    }


@pytest.fixture
def storage_dirs(tmp_path: Path, valid_seed_data: dict[str, dict]) -> tuple[Path, Path]:
    """Khởi tạo thư mục seed và runtime độc lập hoàn toàn trong tmp_path."""
    seed_dir = tmp_path / "seed"
    runtime_dir = tmp_path / "runtime"
    seed_dir.mkdir(parents=True, exist_ok=True)

    for filename, payload in valid_seed_data.items():
        _write_json(seed_dir / filename, payload)

    return seed_dir, runtime_dir


# =====================================================================
# 1. KIỂM THỬ TỰ PHỤC HỒI (AUTO-SEED) & ĐỌC DỮ LIỆU HỢP LỆ
# =====================================================================


def test_load_all_auto_copies_missing_runtime_files(storage_dirs: tuple[Path, Path]) -> None:
    """Khi runtime chưa tồn tại hoặc thiếu file, load_all() tự động copy từ seed sang."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)

    assert not runtime_dir.exists()

    state = storage.load_all()

    # Kiểm tra 4 file đã được copy sang runtime
    for filename in JsonStorage.REQUIRED_FILES:
        assert (runtime_dir / filename).exists()

    # Kiểm tra đối tượng trả về đúng kiểu và dữ liệu
    assert isinstance(state["graph"], RoadGraph)
    assert set(state["graph"].nodes()) == {"N1", "N2", "N3"}
    assert len(state["graph"].edges()) == 2

    assert set(state["locations"].keys()) == {"N1", "N2", "N3"}
    assert isinstance(state["locations"]["N1"], Location)
    assert state["locations"]["N1"].name == "Đại học Bách Khoa"

    assert set(state["drivers"].keys()) == {"D1", "D2"}
    assert isinstance(state["drivers"]["D1"], Driver)
    assert state["drivers"]["D1"].status == FREE

    assert len(state["requests"]) == 2
    assert isinstance(state["requests"][0], RideRequest)

    assert len(state["trips"]) == 1
    assert isinstance(state["trips"][0], Trip)
    assert state["trips"][0].eta == 4.0


def test_load_all_partial_missing_file_recovery(storage_dirs: tuple[Path, Path]) -> None:
    """Nếu chỉ bị xóa 1 file trong runtime (vd: trips.json), chỉ phục hồi đúng file đó từ seed."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)

    storage.load_all()
    (runtime_dir / "trips.json").unlink()
    assert not (runtime_dir / "trips.json").exists()

    state = storage.load_all()
    assert (runtime_dir / "trips.json").exists()
    assert len(state["trips"]) == 1


def test_load_all_missing_seed_file_raises_storage_error(tmp_path: Path) -> None:
    """Ném StorageError nếu cả runtime lẫn seed đều thiếu file."""
    empty_seed = tmp_path / "empty_seed"
    runtime_dir = tmp_path / "runtime"
    empty_seed.mkdir()

    storage = JsonStorage(seed_dir=empty_seed, runtime_dir=runtime_dir)

    with pytest.raises(StorageError):
        storage.load_all()


# =====================================================================
# 2. KIỂM THỬ GHI AN TOÀN (ATOMIC WRITE) & BẢO TOÀN SEED
# =====================================================================


def test_save_all_roundtrip_and_does_not_touch_seed(storage_dirs: tuple[Path, Path]) -> None:
    """Kiểm tra chu trình load -> chỉnh sửa -> save_all -> load lại và không làm bẩn seed."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)

    seed_snapshot_before = {
        f: (seed_dir / f).read_text(encoding="utf-8")
        for f in JsonStorage.REQUIRED_FILES
    }

    state = storage.load_all()

    # Thay đổi dữ liệu trên RAM: thêm tài xế D3, thêm yêu cầu R3, hoàn thành chuyến T1
    state["drivers"]["D3"] = Driver(id="D3", name="Lê Hoàng Cường", node="N3", status=FREE)
    state["requests"].append(
        RideRequest(id="R3", pickup_node="N3", dropoff_node="N1", status=QUEUED)
    )
    state["trips"][0].status = COMPLETED

    storage.save_all(state)

    # Không còn file .tmp nào sót lại sau khi ghi thành công
    assert list(runtime_dir.glob("*.tmp")) == []

    # Dữ liệu gốc trong seed_dir phải nguyên vẹn 100%
    seed_snapshot_after = {
        f: (seed_dir / f).read_text(encoding="utf-8")
        for f in JsonStorage.REQUIRED_FILES
    }
    assert seed_snapshot_before == seed_snapshot_after

    # Đọc lại từ runtime để kiểm tra dữ liệu mới đã được lưu bền vững
    reloaded = storage.load_all()
    assert "D3" in reloaded["drivers"]
    assert reloaded["drivers"]["D3"].name == "Lê Hoàng Cường"
    assert len(reloaded["requests"]) == 3
    assert reloaded["trips"][0].status == COMPLETED


def test_save_all_missing_required_state_key_raises_error(storage_dirs: tuple[Path, Path]) -> None:
    """Ném StorageError khi dict truyền vào save_all() thiếu khóa bắt buộc."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)

    with pytest.raises(StorageError):
        storage.save_all({"graph": RoadGraph()})


# =====================================================================
# 3. KIỂM THỬ BẮT LỖI CÚ PHÁP JSON & THIẾU KHÓA GỐC (STORAGE ERROR)
# =====================================================================


def test_corrupted_or_empty_json_raises_storage_error(storage_dirs: tuple[Path, Path]) -> None:
    """Ném StorageError khi file JSON trong runtime bị rỗng hoặc vỡ cú pháp."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)
    storage.load_all()

    # Làm hỏng file drivers.json (cụt cú pháp JSON)
    (runtime_dir / "drivers.json").write_text("{broken_json: [", encoding="utf-8")

    with pytest.raises(StorageError):
        storage.load_all()


@pytest.mark.parametrize(
    ("filename", "invalid_payload"),
    [
        ("graph.json", {"nodes": []}),  # Thiếu khóa 'edges'
        ("drivers.json", {"wrong_key": []}),  # Thiếu khóa 'drivers'
        ("requests.json", {"requests": "not_a_list"}),  # Khóa gốc không phải list
        ("trips.json", []),  # Gốc không phải dict
    ],
)
def test_missing_root_keys_or_wrong_type_raises_storage_error(
    storage_dirs: tuple[Path, Path],
    filename: str,
    invalid_payload: dict | list,
) -> None:
    """Ném StorageError khi file JSON thiếu khóa gốc bắt buộc hoặc sai kiểu dữ liệu."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)
    storage.load_all()

    _write_json(runtime_dir / filename, invalid_payload)

    with pytest.raises(StorageError):
        storage.load_all()


# =====================================================================
# 4. KIỂM THỬ THAM CHIẾU ID KHÔNG TỒN TẠI (FOREIGN KEY VALIDATION)
# =====================================================================


def test_edge_references_unknown_node_raises_storage_error(storage_dirs: tuple[Path, Path]) -> None:
    """Ném StorageError khi cạnh trong graph.json nối tới đỉnh không tồn tại."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)
    storage.load_all()

    bad_graph = {
        "nodes": [{"id": "N1", "name": "Đỉnh 1"}],
        "edges": [{"from": "N1", "to": "N99", "weight": 5.0}],
    }
    _write_json(runtime_dir / "graph.json", bad_graph)

    with pytest.raises(StorageError):
        storage.load_all()


def test_driver_at_unknown_node_raises_storage_error(storage_dirs: tuple[Path, Path]) -> None:
    """Ném StorageError khi tài xế đứng ở đỉnh không có trên đồ thị."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)
    storage.load_all()

    bad_drivers = {
        "drivers": [{"id": "D1", "name": "An", "node": "N999", "status": FREE}]
    }
    _write_json(runtime_dir / "drivers.json", bad_drivers)

    with pytest.raises(StorageError):
        storage.load_all()


def test_request_with_unknown_pickup_or_dropoff_raises_storage_error(
    storage_dirs: tuple[Path, Path],
) -> None:
    """Ném StorageError khi yêu cầu đặt xe có điểm đón/trả không tồn tại trên đồ thị."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)
    storage.load_all()

    bad_requests = {
        "requests": [
            {"id": "R1", "pickup_node": "N1", "dropoff_node": "N_GHOST", "status": QUEUED}
        ]
    }
    _write_json(runtime_dir / "requests.json", bad_requests)

    with pytest.raises(StorageError):
        storage.load_all()


def test_trip_references_unknown_driver_or_request_raises_storage_error(
    storage_dirs: tuple[Path, Path],
) -> None:
    """Ném StorageError khi chuyến đi tham chiếu tới driver_id hoặc request_id không tồn tại."""
    seed_dir, runtime_dir = storage_dirs
    storage = JsonStorage(seed_dir=seed_dir, runtime_dir=runtime_dir)
    storage.load_all()

    bad_trips = {
        "trips": [
            {"id": "T1", "request_id": "R1", "driver_id": "D_UNKNOWN", "eta": 5.0, "status": ASSIGNED}
        ]
    }
    _write_json(runtime_dir / "trips.json", bad_trips)

    with pytest.raises(StorageError):
        storage.load_all()