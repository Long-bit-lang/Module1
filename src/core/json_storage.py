"""Module quản lý lưu trữ dữ liệu JSON an toàn cho hệ thống điều phối đặt xe."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from core.road_graph import RoadGraph
from models import ASSIGNED, BUSY, FREE, QUEUED, Driver, Location, RideRequest, Trip

_ROOT = Path(__file__).resolve().parents[2]


class StorageError(Exception):
    """Ngoại lệ được ném ra khi file JSON lỗi định dạng, thiếu khóa gốc hoặc sai tham chiếu ID."""


class JsonStorage:
    """Quản lý đọc/ghi dữ liệu thực thể giữa bộ nhớ và các file JSON trong data/runtime/."""

    REQUIRED_FILES: tuple[str, ...] = (
        "graph.json",
        "drivers.json",
        "requests.json",
        "trips.json",
    )

    def __init__(
        self,
        seed_dir: str | Path = _ROOT / "data" / "seed",
        runtime_dir: str | Path = _ROOT / "data" / "runtime",
    ) -> None:
        self.seed_dir = Path(seed_dir)
        self.runtime_dir = Path(runtime_dir)

    def _ensure_runtime_files(self) -> None:
        """Tự động khởi tạo thư mục runtime và sao chép các file thiếu từ seed."""
        try:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"Không thể tạo thư mục runtime tại '{self.runtime_dir}': {exc}") from exc

        for filename in self.REQUIRED_FILES:
            runtime_file = self.runtime_dir / filename
            if not runtime_file.exists():
                seed_file = self.seed_dir / filename
                if not seed_file.exists():
                    raise StorageError(
                        f"Thiếu file dữ liệu chạy '{runtime_file}' và không tìm thấy file mẫu '{seed_file}'."
                    )
                try:
                    shutil.copy2(seed_file, runtime_file)
                except OSError as exc:
                    raise StorageError(f"Không thể sao chép file mẫu '{filename}' sang runtime: {exc}") from exc

    def _read_json(self, filename: str, required_keys: tuple[str, ...]) -> dict[str, Any]:
        """Đọc file JSON từ runtime và kiểm tra cấu trúc khóa gốc bắt buộc."""
        file_path = self.runtime_dir / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise StorageError(f"File '{filename}' bị lỗi cú pháp JSON: {exc}") from exc
        except OSError as exc:
            raise StorageError(f"Không thể đọc file '{filename}': {exc}") from exc

        if not isinstance(data, dict):
            raise StorageError(f"Nội dung gốc của file '{filename}' phải là một JSON object (dict).")

        for key in required_keys:
            if key not in data:
                raise StorageError(f"File '{filename}' thiếu khóa gốc bắt buộc: '{key}'.")
            if not isinstance(data[key], list):
                raise StorageError(f"Khóa '{key}' trong file '{filename}' phải là một danh sách (list).")

        return data

    def _write_atomic(self, payloads: dict[str, dict[str, Any]]) -> None:
        """Ghi an toàn nhiều file: ghi toàn bộ file .tmp trước rồi replace đồng loạt."""
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        written_tmps: list[tuple[Path, Path]] = []
        try:
            for filename, payload in payloads.items():
                target = self.runtime_dir / filename
                tmp = self.runtime_dir / f"{filename}.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                written_tmps.append((tmp, target))

            for tmp, target in written_tmps:
                os.replace(tmp, target)
        except Exception as exc:
            for tmp, _ in written_tmps:
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
            if isinstance(exc, StorageError):
                raise
            raise StorageError(f"Lỗi khi lưu trữ an toàn trạng thái hệ thống: {exc}") from exc

    @staticmethod
    def _validate_business_consistency(
        drivers: dict[str, Driver] | list[Driver],
        requests: list[RideRequest],
        trips: list[Trip],
    ) -> None:
        """Kiểm tra tính nhất quán trạng thái nghiệp vụ giữa Drivers, Requests và Trips theo CONTRACT."""
        driver_iterable = drivers.values() if isinstance(drivers, dict) else drivers
        active_trips = [t for t in trips if t.status == ASSIGNED]
        active_driver_ids: set[str] = set()
        active_request_ids: set[str] = set()

        for t in active_trips:
            if t.driver_id in active_driver_ids:
                raise StorageError(f"Tài xế '{t.driver_id}' đang được gán cho nhiều hơn một chuyến đi chưa hoàn thành.")
            if t.request_id in active_request_ids:
                raise StorageError(f"Yêu cầu '{t.request_id}' đang được gán cho nhiều hơn một chuyến đi chưa hoàn thành.")
            active_driver_ids.add(t.driver_id)
            active_request_ids.add(t.request_id)

        for d in driver_iterable:
            if d.status == BUSY and d.id not in active_driver_ids:
                raise StorageError(f"Tài xế '{d.id}' có trạng thái '{d.status}' nhưng không có chuyến đi đang thực hiện ({ASSIGNED}).")
            if d.status == FREE and d.id in active_driver_ids:
                raise StorageError(f"Tài xế '{d.id}' có trạng thái '{d.status}' nhưng đang được gán cho chuyến đi chưa hoàn thành.")

        all_trip_request_ids = {t.request_id for t in trips}
        for r in requests:
            if r.status == ASSIGNED and r.id not in all_trip_request_ids:
                raise StorageError(f"Yêu cầu '{r.id}' có trạng thái '{r.status}' nhưng không tìm thấy chuyến đi nào trong lịch sử chuyến.")
            if r.status == QUEUED and r.id in active_request_ids:
                raise StorageError(f"Yêu cầu '{r.id}' có trạng thái '{r.status}' nhưng đang được gán cho một chuyến đi chưa hoàn thành.")

    def load_all(self) -> dict[str, Any]:
        """Nạp toàn bộ dữ liệu từ runtime (tự phục hồi từ seed nếu thiếu) và kiểm tra tham chiếu."""
        self._ensure_runtime_files()

        graph_raw = self._read_json("graph.json", ("nodes", "edges"))
        drivers_raw = self._read_json("drivers.json", ("drivers",))
        requests_raw = self._read_json("requests.json", ("requests",))
        trips_raw = self._read_json("trips.json", ("trips",))

        graph = RoadGraph()
        locations: dict[str, Location] = {}

        # 1. Đỉnh đồ thị & địa danh
        for item in graph_raw["nodes"]:
            if not isinstance(item, dict):
                raise StorageError("Mỗi phần tử trong 'nodes' của graph.json phải là một dict.")
            try:
                loc = Location.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"Dữ liệu đỉnh (node) không hợp lệ trong graph.json: {exc}") from exc
            if loc.id in locations:
                raise StorageError(f"Trùng lặp mã đỉnh '{loc.id}' trong graph.json.")
            locations[loc.id] = loc
            graph.add_node(loc.id)

        # 2. Cạnh đồ thị
        for edge in graph_raw["edges"]:
            if not isinstance(edge, dict):
                raise StorageError("Mỗi phần tử trong 'edges' của graph.json phải là một dict.")
            try:
                u, v, weight = str(edge["from"]), str(edge["to"]), float(edge["weight"])
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(
                    f"Cạnh trong graph.json thiếu trường bắt buộc ('from', 'to', 'weight') hoặc sai kiểu: {exc}"
                ) from exc
            if not graph.has_node(u):
                raise StorageError(f"Cạnh tham chiếu đến đỉnh xuất phát '{u}' không tồn tại trong graph.json.")
            if not graph.has_node(v):
                raise StorageError(f"Cạnh tham chiếu đến đỉnh đích '{v}' không tồn tại trong graph.json.")
            try:
                graph.add_edge(u, v, weight)
            except ValueError as exc:
                raise StorageError(f"Trọng số cạnh ({u} -> {v}) không hợp lệ: {exc}") from exc

        # 3. Tài xế
        drivers: dict[str, Driver] = {}
        for item in drivers_raw["drivers"]:
            if not isinstance(item, dict):
                raise StorageError("Mỗi phần tử trong 'drivers' của drivers.json phải là một dict.")
            try:
                d = Driver.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"Dữ liệu tài xế không hợp lệ trong drivers.json: {exc}") from exc
            if d.id in drivers:
                raise StorageError(f"Trùng lặp mã tài xế '{d.id}' trong drivers.json.")
            if not graph.has_node(d.node):
                raise StorageError(f"Tài xế '{d.id}' tham chiếu đến đỉnh '{d.node}' không tồn tại trên đồ thị.")
            drivers[d.id] = d

        # 4. Yêu cầu đặt xe
        requests: list[RideRequest] = []
        request_ids: set[str] = set()
        for item in requests_raw["requests"]:
            if not isinstance(item, dict):
                raise StorageError("Mỗi phần tử trong 'requests' của requests.json phải là một dict.")
            try:
                r = RideRequest.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"Dữ liệu yêu cầu không hợp lệ trong requests.json: {exc}") from exc
            if r.id in request_ids:
                raise StorageError(f"Trùng lặp mã yêu cầu '{r.id}' trong requests.json.")
            if not graph.has_node(r.pickup_node):
                raise StorageError(f"Yêu cầu '{r.id}' có điểm đón '{r.pickup_node}' không tồn tại trên đồ thị.")
            if not graph.has_node(r.dropoff_node):
                raise StorageError(f"Yêu cầu '{r.id}' có điểm trả '{r.dropoff_node}' không tồn tại trên đồ thị.")
            request_ids.add(r.id)
            requests.append(r)

        # 5. Chuyến đi
        trips: list[Trip] = []
        trip_ids: set[str] = set()
        for item in trips_raw["trips"]:
            if not isinstance(item, dict):
                raise StorageError("Mỗi phần tử trong 'trips' của trips.json phải là một dict.")
            try:
                t = Trip.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"Dữ liệu chuyến đi không hợp lệ trong trips.json: {exc}") from exc
            if t.id in trip_ids:
                raise StorageError(f"Trùng lặp mã chuyến đi '{t.id}' trong trips.json.")
            if t.request_id not in request_ids:
                raise StorageError(f"Chuyến đi '{t.id}' tham chiếu đến request_id '{t.request_id}' không tồn tại.")
            if t.driver_id not in drivers:
                raise StorageError(f"Chuyến đi '{t.id}' tham chiếu đến driver_id '{t.driver_id}' không tồn tại.")
            trip_ids.add(t.id)
            trips.append(t)

        # 6. Ràng buộc trạng thái nghiệp vụ
        self._validate_business_consistency(drivers, requests, trips)

        return {
            "graph": graph,
            "drivers": drivers,
            "requests": requests,
            "trips": trips,
            "locations": locations,
        }

    def save_all(self, state: dict[str, Any]) -> None:
        """Chuyển đổi trạng thái các đối tượng thực thể qua to_dict() và lưu an toàn vào runtime."""
        if not isinstance(state, dict):
            raise StorageError("Trạng thái truyền vào save_all() phải là một dict.")

        for key in ("graph", "drivers", "requests", "trips", "locations"):
            if key not in state:
                raise StorageError(f"Trạng thái truyền vào save_all() thiếu khóa bắt buộc: '{key}'.")

        graph, locations = state["graph"], state["locations"]
        if not isinstance(graph, RoadGraph):
            raise StorageError("Trường 'graph' trong state phải là một instance của RoadGraph.")
        if not isinstance(locations, dict):
            raise StorageError("Trường 'locations' trong state phải là một dict.")

        # 1. Graph & Locations
        for node in graph.nodes():
            if node not in locations:
                raise StorageError(f"Location và graph không đồng bộ: '{node}'.")
            if not isinstance(locations[node], Location):
                raise StorageError(f"Phần tử trong 'locations' phải là instance của Location: '{node}'.")

        for u, v, _ in graph.edges():
            if not graph.has_node(u):
                raise StorageError(f"Cạnh tham chiếu đến đỉnh xuất phát '{u}' không tồn tại trên đồ thị.")
            if not graph.has_node(v):
                raise StorageError(f"Cạnh tham chiếu đến đỉnh đích '{v}' không tồn tại trên đồ thị.")

        # 2. Drivers
        raw_drivers = state["drivers"]
        if not isinstance(raw_drivers, (dict, list, tuple)):
            raise StorageError("Trường 'drivers' trong state phải là dict hoặc list.")
        drivers: list[Driver] = []
        driver_ids: set[str] = set()
        for d in (raw_drivers.values() if isinstance(raw_drivers, dict) else raw_drivers):
            if not isinstance(d, Driver):
                raise StorageError(f"Phần tử trong 'drivers' phải là instance của Driver: {d}")
            if d.id in driver_ids:
                raise StorageError(f"Trùng lặp mã tài xế '{d.id}' trong state['drivers'].")
            if not graph.has_node(d.node):
                raise StorageError(f"Tài xế '{d.id}' tham chiếu đến đỉnh '{d.node}' không tồn tại trên đồ thị.")
            driver_ids.add(d.id)
            drivers.append(d)

        # 3. Requests
        raw_requests = state["requests"]
        if not isinstance(raw_requests, (dict, list, tuple)):
            raise StorageError("Trường 'requests' trong state phải là list hoặc dict.")
        requests: list[RideRequest] = []
        request_ids: set[str] = set()
        for r in (raw_requests.values() if isinstance(raw_requests, dict) else raw_requests):
            if not isinstance(r, RideRequest):
                raise StorageError(f"Phần tử trong 'requests' phải là instance của RideRequest: {r}")
            if r.id in request_ids:
                raise StorageError(f"Trùng lặp mã yêu cầu '{r.id}' trong state['requests'].")
            if not graph.has_node(r.pickup_node):
                raise StorageError(f"Yêu cầu '{r.id}' có điểm đón '{r.pickup_node}' không tồn tại trên đồ thị.")
            if not graph.has_node(r.dropoff_node):
                raise StorageError(f"Yêu cầu '{r.id}' có điểm trả '{r.dropoff_node}' không tồn tại trên đồ thị.")
            request_ids.add(r.id)
            requests.append(r)

        # 4. Trips
        raw_trips = state["trips"]
        if not isinstance(raw_trips, (dict, list, tuple)):
            raise StorageError("Trường 'trips' trong state phải là list hoặc dict.")
        trips: list[Trip] = []
        trip_ids: set[str] = set()
        for t in (raw_trips.values() if isinstance(raw_trips, dict) else raw_trips):
            if not isinstance(t, Trip):
                raise StorageError(f"Phần tử trong 'trips' phải là instance của Trip: {t}")
            if t.id in trip_ids:
                raise StorageError(f"Trùng lặp mã chuyến đi '{t.id}' trong state['trips'].")
            if t.request_id not in request_ids:
                raise StorageError(f"Chuyến đi '{t.id}' tham chiếu đến request_id '{t.request_id}' không tồn tại.")
            if t.driver_id not in driver_ids:
                raise StorageError(f"Chuyến đi '{t.id}' tham chiếu đến driver_id '{t.driver_id}' không tồn tại.")
            trip_ids.add(t.id)
            trips.append(t)

        # 5. Ràng buộc trạng thái nghiệp vụ
        self._validate_business_consistency(drivers, requests, trips)

        # 6. Ghi đĩa an toàn
        self._write_atomic({
            "graph.json": {
                "nodes": [locations[n].to_dict() for n in graph.nodes()],
                "edges": [{"from": u, "to": v, "weight": float(w)} for u, v, w in graph.edges()],
            },
            "drivers.json": {"drivers": [d.to_dict() for d in drivers]},
            "requests.json": {"requests": [r.to_dict() for r in requests]},
            "trips.json": {"trips": [t.to_dict() for t in trips]},
        })