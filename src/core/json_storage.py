"""Module quản lý lưu trữ dữ liệu JSON an toàn cho hệ thống điều phối đặt xe."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from core.road_graph import RoadGraph
from models.driver import Driver
from models.location import Location
from models.ride_request import RideRequest
from models.trip import Trip

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
            raise StorageError(
                f"Không thể tạo thư mục runtime tại '{self.runtime_dir}': {exc}"
            ) from exc

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
                    raise StorageError(
                        f"Không thể sao chép file mẫu '{filename}' sang runtime: {exc}"
                    ) from exc

    def _read_json(self, filename: str, required_keys: tuple[str, ...]) -> dict[str, Any]:
        """Đọc file JSON từ runtime và kiểm tra cấu trúc khóa gốc bắt buộc."""
        file_path = self.runtime_dir / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"File '{filename}' bị lỗi cú pháp JSON: {exc}"
            ) from exc
        except OSError as exc:
            raise StorageError(
                f"Không thể đọc file '{filename}': {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise StorageError(
                f"Nội dung gốc của file '{filename}' phải là một JSON object (dict)."
            )

        for key in required_keys:
            if key not in data:
                raise StorageError(
                    f"File '{filename}' thiếu khóa gốc bắt buộc: '{key}'."
                )
            if not isinstance(data[key], list):
                raise StorageError(
                    f"Khóa '{key}' trong file '{filename}' phải là một danh sách (list)."
                )

        return data

    def _atomic_write(self, filename: str, payload: dict[str, Any]) -> None:
        """Ghi dữ liệu ra file tạm (.tmp) rồi thay thế nguyên tử sang file đích."""
        try:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(
                f"Không thể tạo thư mục runtime '{self.runtime_dir}': {exc}"
            ) from exc

        target_path = self.runtime_dir / filename
        tmp_path = self.runtime_dir / f"{filename}.tmp"

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target_path)
        except (OSError, TypeError, ValueError) as exc:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise StorageError(
                f"Lỗi khi ghi file an toàn '{filename}': {exc}"
            ) from exc

    def load_all(self) -> dict[str, Any]:
        """Nạp toàn bộ dữ liệu từ runtime (tự phục hồi từ seed nếu thiếu) và kiểm tra tham chiếu."""
        self._ensure_runtime_files()

        graph_raw = self._read_json("graph.json", ("nodes", "edges"))
        drivers_raw = self._read_json("drivers.json", ("drivers",))
        requests_raw = self._read_json("requests.json", ("requests",))
        trips_raw = self._read_json("trips.json", ("trips",))

        graph = RoadGraph()
        locations: dict[str, Location] = {}

        # 1. Nạp danh sách đỉnh & địa danh (Location + RoadGraph nodes)
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

        # 2. Nạp danh sách cạnh (RoadGraph edges) và kiểm tra đỉnh tồn tại
        for edge in graph_raw["edges"]:
            if not isinstance(edge, dict):
                raise StorageError("Mỗi phần tử trong 'edges' của graph.json phải là một dict.")
            try:
                u = str(edge["from"])
                v = str(edge["to"])
                weight = float(edge["weight"])
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(
                    f"Cạnh trong graph.json thiếu trường bắt buộc ('from', 'to', 'weight') hoặc sai kiểu: {exc}"
                ) from exc

            if not graph.has_node(u):
                raise StorageError(
                    f"Cạnh tham chiếu đến đỉnh xuất phát '{u}' không tồn tại trong graph.json."
                )
            if not graph.has_node(v):
                raise StorageError(
                    f"Cạnh tham chiếu đến đỉnh đích '{v}' không tồn tại trong graph.json."
                )

            try:
                graph.add_edge(u, v, weight)
            except ValueError as exc:
                raise StorageError(f"Trọng số cạnh ({u} -> {v}) không hợp lệ: {exc}") from exc

        # 3. Nạp danh sách tài xế (Drivers) và kiểm tra node đứng
        drivers: dict[str, Driver] = {}
        for item in drivers_raw["drivers"]:
            if not isinstance(item, dict):
                raise StorageError("Mỗi phần tử trong 'drivers' của drivers.json phải là một dict.")
            try:
                driver = Driver.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"Dữ liệu tài xế không hợp lệ trong drivers.json: {exc}") from exc

            if driver.id in drivers:
                raise StorageError(f"Trùng lặp mã tài xế '{driver.id}' trong drivers.json.")
            if not graph.has_node(driver.node):
                raise StorageError(
                    f"Tài xế '{driver.id}' tham chiếu đến đỉnh '{driver.node}' không tồn tại trên đồ thị."
                )

            drivers[driver.id] = driver

        # 4. Nạp danh sách yêu cầu đặt xe (RideRequests) và kiểm tra điểm đón/trả
        requests: list[RideRequest] = []
        request_ids: set[str] = set()
        for item in requests_raw["requests"]:
            if not isinstance(item, dict):
                raise StorageError("Mỗi phần tử trong 'requests' của requests.json phải là một dict.")
            try:
                req = RideRequest.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"Dữ liệu yêu cầu không hợp lệ trong requests.json: {exc}") from exc

            if req.id in request_ids:
                raise StorageError(f"Trùng lặp mã yêu cầu '{req.id}' trong requests.json.")
            if not graph.has_node(req.pickup_node):
                raise StorageError(
                    f"Yêu cầu '{req.id}' có điểm đón '{req.pickup_node}' không tồn tại trên đồ thị."
                )
            if not graph.has_node(req.dropoff_node):
                raise StorageError(
                    f"Yêu cầu '{req.id}' có điểm trả '{req.dropoff_node}' không tồn tại trên đồ thị."
                )

            request_ids.add(req.id)
            requests.append(req)

        # 5. Nạp danh sách chuyến đi (Trips) và kiểm tra tham chiếu request_id, driver_id
        trips: list[Trip] = []
        trip_ids: set[str] = set()
        for item in trips_raw["trips"]:
            if not isinstance(item, dict):
                raise StorageError("Mỗi phần tử trong 'trips' của trips.json phải là một dict.")
            try:
                trip = Trip.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                raise StorageError(f"Dữ liệu chuyến đi không hợp lệ trong trips.json: {exc}") from exc

            if trip.id in trip_ids:
                raise StorageError(f"Trùng lặp mã chuyến đi '{trip.id}' trong trips.json.")
            if trip.request_id not in request_ids:
                raise StorageError(
                    f"Chuyến đi '{trip.id}' tham chiếu đến request_id '{trip.request_id}' không tồn tại."
                )
            if trip.driver_id not in drivers:
                raise StorageError(
                    f"Chuyến đi '{trip.id}' tham chiếu đến driver_id '{trip.driver_id}' không tồn tại."
                )

            trip_ids.add(trip.id)
            trips.append(trip)

        # 6. Kiểm tra tính nhất quán trạng thái nghiệp vụ giữa Drivers, Requests và Trips
        active_trips = [t for t in trips if t.status == "assigned"]
        active_driver_ids: set[str] = set()
        active_request_ids: set[str] = set()

        for t in active_trips:
            if t.driver_id in active_driver_ids:
                raise StorageError(
                    f"Tài xế '{t.driver_id}' đang được gán cho nhiều hơn một chuyến đi chưa hoàn thành."
                )
            if t.request_id in active_request_ids:
                raise StorageError(
                    f"Yêu cầu '{t.request_id}' đang được gán cho nhiều hơn một chuyến đi chưa hoàn thành."
                )
            active_driver_ids.add(t.driver_id)
            active_request_ids.add(t.request_id)

        for driver in drivers.values():
            if driver.status == "busy" and driver.id not in active_driver_ids:
                raise StorageError(
                    f"Tài xế '{driver.id}' có trạng thái '{driver.status}' nhưng không có chuyến đi đang thực hiện (assigned)."
                )
            if driver.status == "free" and driver.id in active_driver_ids:
                raise StorageError(
                    f"Tài xế '{driver.id}' có trạng thái '{driver.status}' nhưng đang được gán cho chuyến đi chưa hoàn thành."
                )

        all_trip_request_ids = {t.request_id for t in trips}
        for req in requests:
            if req.status == "assigned" and req.id not in all_trip_request_ids:
                raise StorageError(
                    f"Yêu cầu '{req.id}' có trạng thái '{req.status}' nhưng không tìm thấy chuyến đi nào trong lịch sử chuyến."
                )
            if req.status == "queued" and req.id in active_request_ids:
                raise StorageError(
                    f"Yêu cầu '{req.id}' có trạng thái '{req.status}' nhưng đang được gán cho một chuyến đi chưa hoàn thành."
                )

        return {
            "graph": graph,
            "drivers": drivers,
            "requests": requests,
            "trips": trips,
            "locations": locations,
        }

    def save_all(self, state: dict[str, Any]) -> None:
        """Chuyển đổi trạng thái các đối tượng thực thể qua to_dict() và lưu an toàn vào runtime.
        
        Áp dụng cơ chế atomic từng file kết hợp chuẩn bị toàn bộ file .tmp trước khi hoán đổi (os.replace)
        để giảm thiểu tối đa rủi ro không nhất quán dữ liệu giữa các file JSON.
        """
        if not isinstance(state, dict):
            raise StorageError("Trạng thái truyền vào save_all() phải là một dict.")

        required_state_keys = ("graph", "drivers", "requests", "trips", "locations")
        for key in required_state_keys:
            if key not in state:
                raise StorageError(f"Trạng thái truyền vào save_all() thiếu khóa bắt buộc: '{key}'.")

        graph: RoadGraph = state["graph"]
        locations: dict[str, Location] = state.get("locations") or {}

        written_tmp_files: list[tuple[Path, Path]] = []
        try:
            # 1. Chuẩn bị dữ liệu cho graph.json
            nodes_payload: list[dict[str, Any]] = []
            for node_id in graph.nodes():
                if node_id in locations:
                    nodes_payload.append(locations[node_id].to_dict())
                else:
                    raise StorageError(f"Location và graph không đồng bộ: '{node_id}'.")

            edges_payload: list[dict[str, Any]] = [
                {"from": u, "to": v, "weight": float(w)}
                for u, v, w in graph.edges()
            ]

            # 2. Chuẩn bị dữ liệu cho drivers.json (hỗ trợ cả dict[str, Driver] lẫn list[Driver])
            raw_drivers = state["drivers"]
            driver_iterable = (
                raw_drivers.values() if isinstance(raw_drivers, dict) else raw_drivers
            )
            drivers_payload = [driver.to_dict() for driver in driver_iterable]

            # 3. Chuẩn bị dữ liệu cho requests.json (hỗ trợ cả list[RideRequest] lẫn dict[str, RideRequest])
            raw_requests = state["requests"]
            request_iterable = (
                raw_requests.values() if isinstance(raw_requests, dict) else raw_requests
            )
            requests_payload = [req.to_dict() for req in request_iterable]

            # 4. Chuẩn bị dữ liệu cho trips.json
            raw_trips = state["trips"]
            trip_iterable = (
                raw_trips.values() if isinstance(raw_trips, dict) else raw_trips
            )
            trips_payload = [trip.to_dict() for trip in trip_iterable]

            payloads = {
                "graph.json": {"nodes": nodes_payload, "edges": edges_payload},
                "drivers.json": {"drivers": drivers_payload},
                "requests.json": {"requests": requests_payload},
                "trips.json": {"trips": trips_payload},
            }

            # 5. Ghi an toàn: ghi và fsync toàn bộ file tạm (.tmp) trước,
            # nếu tất cả đều thành công mới tiến hành os.replace lần lượt.
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            for filename, payload in payloads.items():
                target_path = self.runtime_dir / filename
                tmp_path = self.runtime_dir / f"{filename}.tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                written_tmp_files.append((tmp_path, target_path))

            for tmp_path, target_path in written_tmp_files:
                os.replace(tmp_path, target_path)
        except (AttributeError, KeyError, OSError, TypeError, ValueError) as exc:
            for tmp_path, _ in written_tmp_files:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass
            if isinstance(exc, StorageError):
                raise
            raise StorageError(f"Lỗi khi lưu trữ an toàn trạng thái hệ thống: {exc}") from exc