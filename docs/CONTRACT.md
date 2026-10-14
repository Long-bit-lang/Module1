# Hợp đồng giao tiếp giữa các module (CONTRACT)

> **Lưu ý quan trọng**: Đây là nguồn chân lý duy nhất (Single Source of Truth) về giao diện và chữ ký hàm giữa các module. Mọi thay đổi liên quan đến API hoặc schema dữ liệu JSON bắt buộc phải được thảo luận nhóm và thông qua Pull Request riêng.
> Mỗi thành viên chịu trách nhiệm chính về phần hợp đồng của module mình phụ trách.

---

## 1. Models (Thành viên 1 — Nhi)
- Mọi entity kế thừa `BaseEntity`: có `id: str` ổn định, phương thức `to_dict()` và `from_dict(data: dict)`.
- **Hằng số trạng thái** (export từ `models` để toàn bộ dự án import dùng chung, không hardcode chuỗi):
  - `FREE = "free"`, `BUSY = "busy"`
  - `QUEUED = "queued"`, `ASSIGNED = "assigned"`
  - `COMPLETED = "completed"`
- **Lớp `Location`**:
  - Thuộc tính: `id: str`, `name: str`.
  - Mục đích: Lưu tên địa danh trực quan cho đỉnh đồ thị, tách riêng để `RoadGraph` thuần túy phục vụ thuật toán.
- **Lớp `Driver`**:
  - Thuộc tính: `id: str`, `name: str`, `node: str`, `status: str = FREE`.
  - Phương thức:
    - `assign() -> None`: Chuyển `FREE` → `BUSY`; ném lỗi nếu tài xế đang `BUSY`.
    - `release() -> None`: Chuyển `BUSY` → `FREE`.
- **Lớp `RideRequest`**:
  - Thuộc tính: `id: str`, `pickup_node: str`, `dropoff_node: str`, `status: str = QUEUED`.
- **Lớp `Trip`**:
  - Thuộc tính: `id: str`, `request_id: str`, `driver_id: str`, `eta: float`, `status: str = ASSIGNED`.
  - Trạng thái hợp lệ: `ASSIGNED` hoặc `COMPLETED`.

---

## 2. RoadGraph (Thành viên 2 — Duy)
- Đồ thị có hướng, trọng số cạnh biểu diễn thời gian di chuyển (phút, kiểu `float >= 0`).
- **Giao diện API của `RoadGraph`**:
  - `add_node(id: str) -> None`: Thêm một đỉnh vào đồ thị (hỗ trợ đỉnh cô lập).
  - `has_node(id: str) -> bool`: Kiểm tra sự tồn tại của đỉnh (dùng để validate điểm đón/trả).
  - `add_edge(u: str, v: str, weight: float) -> None`: Thêm cạnh có hướng từ `u` đến `v` với trọng số `weight`.
  - `nodes() -> list[str]`: Trả về danh sách tất cả các mã đỉnh hiện có.
  - `edges() -> list[tuple[str, str, float]]`: Trả về danh sách các cạnh `(u, v, weight)` để `JsonStorage` xuất file `graph.json` mà không cần truy cập biến private `_adj`.
  - `neighbors(u: str) -> list[tuple[str, float]]`: Trả về danh sách láng giềng `(v, weight)` kề sau đỉnh `u`.
  - `reversed() -> RoadGraph`: Trả về một `RoadGraph` mới với tất cả các cạnh được đảo ngược hướng (dùng cho thuật toán A2).

---

## 3. MatchStrategy và Thuật toán (Thành viên 2 — Duy)
- **Cấu trúc kết quả `MatchResult` (dataclass)**:
  - `driver_id: str | None`: Mã tài xế được chọn (None nếu không tìm thấy).
  - `eta: float | None`: Thời gian dự kiến đón tính bằng phút (None nếu không đến được).
  - `visited_count: int`: Tổng số đỉnh được lấy ra (pop) khỏi min-heap trong suốt quá trình chạy thuật toán.
  - `path: list[str] | None`: Danh sách các đỉnh biểu diễn lộ trình đón (nếu có).
  - `runtime_ms: float`: Thời gian thực thi thuật toán tính bằng mili-giây.
- **Lớp trừu tượng `MatchStrategy`**:
  - `find_driver(graph: RoadGraph, pickup_node: str, free_drivers: dict[str, str]) -> MatchResult`
  - Tham số `free_drivers`: Dictionary ánh xạ `{driver_id: node_hien_tai}` của các tài xế đang rảnh.
- **Hai chiến lược cốt lõi**:
  - **A1 (`DijkstraPerDriver`)**: Chạy Dijkstra từ từng tài xế rảnh đến điểm đón, chọn tài xế có ETA nhỏ nhất. `visited_count` cộng dồn qua tất cả các lượt chạy.
  - **A2 (`ReverseDijkstra`)**: Chạy Dijkstra từ điểm đón trên đồ thị đảo chiều `graph.reversed()`; xét tất cả các tài xế rảnh cùng đạt khoảng cách nhỏ nhất rồi mới dừng.
- **Quy tắc giải quyết hòa ETA (Tie-breaking)**:
  - Ưu tiên tài xế có ETA nhỏ nhất; nếu hòa ETA, chọn `driver_id` nhỏ nhất theo thứ tự so sánh chuỗi từ điển (`min(driver_id)`).
  - Cả A1 và A2 phải tuân thủ nghiêm ngặt quy tắc này.
- **Đăng ký chiến lược**:
  - File `src/core/strategies.py` cung cấp sẵn từ điển:
    ```python
    STRATEGIES = {
        "A1 - Dijkstra từng tài xế": DijkstraPerDriver,
        "A2 - Dijkstra đảo chiều": ReverseDijkstra,
    }
    ```
    UI sẽ đọc từ điển này để tự động nạp dropdown mà không cần import từng class thủ công.

---

## 4. Cấu trúc dữ liệu và Undo/Redo (Thành viên 3 — Thông)
- **`RequestQueue` (Hàng đợi FIFO)**:
  - `enqueue(request: RideRequest) -> None`: Thêm yêu cầu vào cuối hàng đợi.
  - `dequeue() -> RideRequest`: Lấy và xóa yêu cầu ở đầu hàng đợi.
  - `peek() -> RideRequest | None`: Xem yêu cầu ở đầu hàng đợi mà không xóa.
  - `requeue_head(request: RideRequest) -> None`: Đưa yêu cầu trở lại **vị trí đầu hàng đợi** (phục vụ thao tác Undo).
  - `__len__() -> int`: Trả về số lượng yêu cầu trong hàng đợi.
- **`Stack` (Ngăn xếp LIFO)**:
  - `push(item: Any) -> None`, `pop() -> Any`, `clear() -> None`, `__len__() -> int`.
- **`UndoManager`**:
  - Quản lý hai ngăn xếp: `undo_stack` và `redo_stack`.
  - Định nghĩa action dataclass:
    ```python
    @dataclass
    class DispatchAction:
        trip: Trip
        driver_id: str
        request: RideRequest
        previous_driver_node: str | None = None
    ```
  - **Phạm vi Undo/Redo**: Chỉ áp dụng cho thao tác điều phối chuyến (`dispatch_next`).
  - Khi phát sinh thao tác điều phối mới: Bắt buộc xóa sạch `redo_stack.clear()`.

---

## 5. Dispatcher — Đầu mối nghiệp vụ (Thành viên 3 — Thông)
- **Nguyên tắc**: Dispatcher không trực tiếp đọc/ghi file (việc lưu trữ thuộc về JsonStorage).
- **Khởi tạo và Quản lý dữ liệu**:
  - `Dispatcher(graph: RoadGraph, drivers: dict[str, Driver], trips: list[Trip] | None = None, all_requests: dict[str, RideRequest] | None = None)`
  - Dispatcher duy trì danh sách toàn bộ các yêu cầu (`all_requests`) để khi `export_state()` có thể ghi đầy đủ cả yêu cầu đang chờ (`queued`) và yêu cầu đã điều phối (`assigned`).
- **Giao diện API của `Dispatcher`**:
  - **Quản lý yêu cầu**:
    - `submit_request(pickup_node: str, dropoff_node: str) -> RideRequest`: Tự động sinh ID theo quy tắc `R` + số thứ tự tăng dần. Kiểm tra tính hợp lệ của `pickup_node` và `dropoff_node` bằng `graph.has_node()`; ném `ValueError` nếu đỉnh không tồn tại. Đặt trạng thái `QUEUED`, thêm vào `all_requests` và `queue.enqueue()`.
  - **Quản lý tài xế**:
    - `add_driver(name: str, node: str) -> Driver`: Tự sinh ID `D` + số, kiểm tra `node`, tạo và lưu Driver.
    - `update_driver(driver_id: str, name: str | None = None, node: str | None = None) -> Driver`: Cập nhật thông tin tài xế.
    - `remove_driver(driver_id: str) -> bool`: Xóa tài xế; ném `ValueError` nếu tài xế đang ở trạng thái `BUSY`.
  - **Điều phối chuyến**:
    - `dispatch_next(strategy: MatchStrategy) -> Trip | None`: Lấy yêu cầu ở đầu hàng đợi (`peek()`). Nếu không có tài xế hoặc không có đường đi, trả về `None` và giữ nguyên yêu cầu ở đầu hàng đợi. Nếu thành công: dequeue request, chuyển request sang `ASSIGNED`, chuyển driver sang `BUSY`, tạo `Trip` mới (ID tự sinh `T` + số), ghi nhận vào `UndoManager` và trả về `Trip`.
  - **Vòng đời tài xế & Hoàn thành chuyến**:
    - `complete_trip(trip_id: str) -> bool`: Tìm chuyến đi tương ứng, đổi `Trip.status` sang `COMPLETED`, gọi `driver.release()` để chuyển tài xế về `FREE`, và cập nhật vị trí tài xế về `dropoff_node` của chuyến. Giúp hệ thống không bị cạn kiệt tài xế khi chạy demo dài.
  - **Hoàn tác & Làm lại**:
    - `can_undo() -> bool`, `can_redo() -> bool`.
    - `undo() -> bool`: Hoàn tác lần điều phối gần nhất; xóa Trip khỏi danh sách, gọi `driver.release()`, chuyển request về `QUEUED` và gọi `queue.requeue_head(request)`.
    - `redo() -> bool`: Tái lập lại lần điều phối vừa hoàn tác.
  - **API Snapshot an toàn cho UI** (trả về bản sao, UI không can thiệp trực tiếp biến nội bộ):
    - `queue_snapshot() -> list[RideRequest]`: Danh sách yêu cầu đang đợi theo thứ tự hàng đợi.
    - `trips_snapshot() -> list[Trip]`: Danh sách lịch sử các chuyến đi.
    - `drivers_snapshot() -> dict[str, Driver]`: Danh sách tài xế hiện có.
  - **Giao tiếp trạng thái với JsonStorage**:
    - `Dispatcher.from_state(state: dict) -> Dispatcher`: Khởi tạo instance từ dữ liệu đã nạp.
    - `Dispatcher.export_state() -> dict`: Trích xuất toàn bộ dữ liệu đối tượng để lưu trữ.

---

## 6. JsonStorage — Lưu trữ an toàn (Thành viên 4 — Thắng)
- **Phân tách thư mục dữ liệu**:
  - `data/seed/`: Chứa dữ liệu mẫu ban đầu (`graph.json`, `drivers.json`, `requests.json`, `trips.json`), được quản lý và commit lên Git. Thắng sở hữu thư mục này.
  - `data/runtime/`: Chứa dữ liệu chạy thực tế khi người dùng thao tác ứng dụng. Thư mục này nằm trong `.gitignore` để tránh phát sinh diff rác và conflict Git.
- **Cơ chế tự phục hồi (Auto-seed)**:
  - Khi gọi `load_all()`, nếu thiếu file trong `data/runtime/`, `JsonStorage` sẽ tự động copy file mẫu từ `data/seed/` sang `data/runtime/`.
- **Ghi an toàn (Atomic File Replacement)**:
  - Khi lưu dữ liệu, luôn ghi ra file tạm (`filename.tmp`) rồi thực hiện atomic replace sang file chính thức nhằm chống mất mát/hỏng file nếu ứng dụng bị ngắt đột ngột.
- **Cấu trúc trạng thái nạp và lưu**:
  - `load_all() -> dict`: Trả về dict các **đối tượng thực thể**:
    ```python
    {
        "graph": RoadGraph,
        "drivers": dict[str, Driver],
        "requests": list[RideRequest],
        "trips": list[Trip],
        "locations": dict[str, Location],
    }
    ```
  - `save_all(state: dict) -> None`: Nhận dict các đối tượng trên, chuyển đổi qua `to_dict()` và ghi an toàn xuống 4 file JSON trong `data/runtime/`.
- **Schema JSON (khóa gốc bắt buộc)**:
  - `graph.json`: `{"nodes": [{"id": "N1", "name": "Ngã tư A"}], "edges": [{"from": "N1", "to": "N2", "weight": 5.0}]}`
  - `drivers.json`: `{"drivers": [{"id": "D1", "name": "An", "node": "N1", "status": "free"}]}`
  - `requests.json`: `{"requests": [{"id": "R1", "pickup_node": "N3", "dropoff_node": "N7", "status": "queued"}]}`
  - `trips.json`: `{"trips": [{"id": "T1", "request_id": "R1", "driver_id": "D1", "eta": 7.0, "status": "assigned"}]}`
- **Quản lý ngoại lệ**:
  - Ném `StorageError(Exception)` kèm thông báo rõ ràng khi file JSON sai định dạng, thiếu khóa gốc hoặc có ID tham chiếu không tồn tại.
- **Kiểm thử**: Mọi unit test của storage phải sử dụng fixture `tmp_path` của pytest, không can thiệp vào `data/seed/`.

---

## 7. UI và Tích hợp ứng dụng (Thành viên 5 — Long)
- **Nguyên tắc**: UI chỉ tương tác qua API công khai của `Dispatcher` và `JsonStorage`. Tuyệt đối không chứa thuật toán Dijkstra hoặc logic quản lý ngăn xếp Undo/Redo.
- **Kiến trúc Module giao diện (`src/ui/`)**:
  - `src/app.py`: Entrypoint mỏng cấu hình layout Streamlit và điều hướng tab.
  - `src/ui/session.py`: Quản lý khởi tạo và lưu giữ instance `Dispatcher` và `JsonStorage` trong `st.session_state`.
  - `src/ui/tab_data.py`: Màn hình xem/thêm/sửa/xóa tài xế, xem đỉnh/cạnh đồ thị, tải lại dữ liệu từ đĩa.
  - `src/ui/tab_dispatch.py`: Màn hình tạo yêu cầu đặt xe, xem hàng đợi, chọn chiến lược từ `STRATEGIES`, nút điều phối, hiển thị kết quả, nút Undo/Redo, danh sách chuyến và nút hoàn thành chuyến.
  - `src/ui/tab_benchmark.py`: Màn hình chạy thực nghiệm đối chuẩn A1 vs A2, hiển thị bảng và biểu đồ so sánh.
- **Bảo toàn lịch sử Undo/Redo**:
  - `Dispatcher` được khởi tạo một lần và lưu trong `st.session_state["dispatcher"]`.
  - Không nạp lại từ file ở mỗi lần Streamlit rerun để hai ngăn xếp Undo/Redo không bị mất.
- **Tự động lưu trạng thái**:
  - UI gọi `save_all(dispatcher.export_state())` ngay sau mỗi thao tác thành công (thêm yêu cầu, điều phối, Undo, Redo, đổi tài xế, hoàn thành chuyến).

---

## 8. Quy định Git, Phân quyền và Quy trình nhóm
- **Phân quyền sở hữu qua `.github/CODEOWNERS`**:
  - `src/models/` : `@Nhi`
  - `src/core/road_graph.py`, `src/core/strategies.py`, `tests/conftest.py` : `@Duy`
  - `src/core/dispatcher.py`, `src/core/structures.py`, `src/core/undo_manager.py` : `@Thong`
  - `src/core/json_storage.py`, `data/seed/` : `@Thang`
  - `src/app.py`, `src/ui/`, `README.md`, `pyproject.toml`, `uv.lock` : `@Long`
- **Quản lý Dependency**:
  - `pyproject.toml` và `uv.lock` do Long phụ trách độc quyền. Thành viên cần thêm thư viện phải thông báo cho Long cập nhật bằng `uv lock`.
- **Lộ trình tích hợp sớm**:
  - **Ngày 1–2**: Merge Core Models (TV1) và RoadGraph API skeleton (TV2) vào `main`.
  - **Ngày 3–4**: Thông viết Dispatcher (test bằng `FakeStrategy`); Thắng viết `JsonStorage`; Long dựng khung `src/ui/`.
  - **Ngày 5**: Ghép Dispatcher với JsonStorage; Duy hoàn thiện A1/A2; Thông chuyển sang A1/A2 thực.
  - **Ngày 6**: Long tích hợp toàn bộ vào UI; chạy kiểm thử tích hợp liên module.
  - **Ngày 7**: Kiểm thử toàn diện, diễn tập demo và hoàn thiện báo cáo.