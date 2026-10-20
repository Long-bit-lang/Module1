# Hợp đồng giao tiếp giữa các module (CONTRACT)

> **Lưu ý quan trọng**: Đây là nguồn chân lý duy nhất (Single Source of Truth) về giao diện và chữ ký hàm giữa các module. Mọi thay đổi liên quan đến API hoặc schema dữ liệu JSON bắt buộc phải được thảo luận nhóm và thông qua Pull Request riêng.
> Mỗi thành viên chịu trách nhiệm chính về phần hợp đồng của module mình phụ trách.

---

## 1. Models (Thành viên 1 — Nhi)
- Mọi entity kế thừa `BaseEntity`: có `id: str` ổn định, phương thức `to_dict()` và `from_dict(data: dict)`.
- **Hằng số trạng thái** (export từ `models` để toàn bộ dự án import dùng chung, không hardcode chuỗi):
  - `FREE = "free"`, `BUSY = "busy"`
  - `QUEUED = "queued"`, `ASSIGNED = "assigned"`, `CANCELLED = "cancelled"`
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
  - Trạng thái hợp lệ: `QUEUED`, `ASSIGNED`, hoặc `CANCELLED`.
- **Lớp `Trip`**:
  - Thuộc tính: `id: str`, `request_id: str`, `driver_id: str`, `eta: float`, `status: str = ASSIGNED`.
  - Trạng thái hợp lệ: `ASSIGNED`, `COMPLETED`, hoặc `CANCELLED`.

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
  - `reversed() -> RoadGraph`: Trả về đồ thị đảo chiều các cạnh (dùng cho thuật toán A2). Có cơ chế cache nội bộ (`_reversed_cache`) để tái sử dụng giữa các lần gọi liên tiếp, tự động vô hiệu hóa (invalidation) khi đồ thị bị thay đổi qua `add_node()` hoặc `add_edge()`.

---

## 3. MatchStrategy và Thuật toán (Thành viên 2 — Duy)
- **Cấu trúc kết quả `MatchResult` (dataclass)**:
  - `driver_id: str | None`: Mã tài xế được chọn (None nếu không tìm thấy).
  - `eta: float | None`: Thời gian dự kiến đón tính bằng phút (None nếu không đến được).
  - `visited_count: int`: Tổng số lần lấy phần tử ra (pop) khỏi min-heap trong suốt quá trình chạy thuật toán (bao gồm mọi lần pop, kể cả các bản cũ của đỉnh đã được thăm trước đó).
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

## 4. Cấu trúc dữ liệu (Thành viên 3 — Thông)
- **`RequestQueue` (Hàng đợi FIFO)**:
  - `enqueue(request: RideRequest) -> None`: Thêm yêu cầu vào cuối hàng đợi.
  - `dequeue() -> RideRequest`: Lấy và xóa yêu cầu ở đầu hàng đợi.
  - `peek() -> RideRequest | None`: Xem yêu cầu ở đầu hàng đợi mà không xóa.
  - `remove(request_id: str) -> bool`: Tìm và xóa yêu cầu theo ID khỏi hàng đợi (dùng khi khách hủy yêu cầu đang chờ); cập nhật chính xác con trỏ `_head`, `_tail` và `_size`; trả về `True` nếu xóa thành công, `False` nếu không tìm thấy.
  - `__len__() -> int`: Trả về số lượng yêu cầu trong hàng đợi.
  - `__iter__() -> Iterator[RideRequest]`: Duyệt tuần tự các yêu cầu trong hàng đợi từ đầu đến cuối mà không làm thay đổi trạng thái.
- **`Stack` (Ngăn xếp LIFO)**:
  - `push(item: Any) -> None`, `pop() -> Any`, `clear() -> None`, `__len__() -> int`.
  - `peek() -> Any | None`: Xem phần tử ở đỉnh ngăn xếp mà không lấy ra (`None` nếu rỗng).
  - `__iter__() -> Iterator[Any]`: Duyệt các phần tử trong ngăn xếp từ đỉnh xuống đáy mà không làm thay đổi trạng thái.

---

## 5. Dispatcher — Đầu mối nghiệp vụ (Thành viên 3 — Thông)
- **Nguyên tắc**: Dispatcher không trực tiếp đọc/ghi file (việc lưu trữ thuộc về JsonStorage).
- **Khởi tạo và Quản lý dữ liệu**:
  - `Dispatcher(graph: RoadGraph, drivers: dict[str, Driver], trips: list[Trip] | None = None, all_requests: dict[str, RideRequest] | None = None, locations: dict[str, Location] | None = None)`
  - Dispatcher duy trì danh sách toàn bộ các yêu cầu (`all_requests`) để khi `export_state()` có thể ghi đầy đủ cả yêu cầu đang chờ (`queued`), yêu cầu đã điều phối (`assigned`) và yêu cầu đã hủy (`cancelled`), đồng thời lưu giữ `locations` phục vụ xuất dữ liệu đồ thị.
  - **Quy tắc sinh ID**: Các bộ đếm ID (`R...`, `D...`, `T...`) được khởi tạo từ số thứ tự lớn nhất hiện có trong dữ liệu nạp vào (`from_state`). ID đã cấp không bao giờ được tái sử dụng.
- **Giao diện API của `Dispatcher`**:
  - **Thuộc tính trạng thái bổ sung**:
    - `last_match_result: MatchResult | None`: Chi tiết thuật toán (visited_count, runtime_ms, path) của lần gọi `dispatch_next` gần nhất.
    - `last_failure: str | None`: Mã nguyên nhân thất bại nếu lần điều phối gần nhất không thành công (`"empty_queue"`, `"no_free_driver"`, `"no_route"`, hoặc `None` nếu thành công).
  - **Quản lý yêu cầu**:
    - `submit_request(pickup_node: str, dropoff_node: str) -> RideRequest`: Tự động sinh ID theo quy tắc `R` + số thứ tự tăng dần. Kiểm tra tính hợp lệ của `pickup_node` và `dropoff_node` bằng `graph.has_node()`. Kiểm tra `pickup_node != dropoff_node` và kiểm tra tồn tại đường đi từ điểm đón đến điểm trả bằng thuật toán tìm đường ngắn nhất; ném `ValueError` kèm thông báo tiếng Việt nếu đỉnh không tồn tại, trùng nhau hoặc không có đường đi. Đặt trạng thái `QUEUED`, thêm vào `all_requests` và `queue.enqueue()`.
    - `cancel_request(request_id: str) -> bool`: Hủy một yêu cầu đang ở trạng thái `QUEUED`. Xóa khỏi hàng đợi `RequestQueue` và từ điển `all_requests`. Trả về `True` nếu hủy thành công, `False` nếu không tìm thấy hoặc yêu cầu đã được điều phối (`ASSIGNED`).
  - **Quản lý tài xế**:
    - `add_driver(name: str, node: str) -> Driver`: Tự sinh ID `D` + số, kiểm tra `node`, tạo và lưu Driver. Tên tài xế được chuẩn hóa qua `strip()`.
    - `update_driver(driver_id: str, name: str | None = None, node: str | None = None) -> Driver`: Cập nhật thông tin tài xế. Không cho phép đổi vị trí nếu tài xế đang `BUSY`. Tên tài xế được chuẩn hóa qua `strip()`.
    - `remove_driver(driver_id: str) -> bool`: Xóa tài xế; ném `ValueError` nếu tài xế đang ở trạng thái `BUSY`, hoặc đã có lịch sử tham gia chuyến đi trong `trips` (bao gồm cả chuyến đã hủy `CANCELLED`).
  - **Điều phối chuyến**:
    - `dispatch_next(strategy: MatchStrategy) -> Trip | None`: Lấy yêu cầu ở đầu hàng đợi (`peek()`). Nếu không có yêu cầu, không có tài xế rảnh, hoặc không có đường đi đến điểm đón: ghi nhận mã lý do thất bại vào `self.last_failure` (`"empty_queue"`, `"no_free_driver"`, `"no_route"`), đặt `self.last_match_result = None`, trả về `None` và giữ nguyên yêu cầu ở đầu hàng đợi. Nếu thành công: dequeue request, chuyển request sang `ASSIGNED`, chuyển driver sang `BUSY`, tạo `Trip` mới (ID tự sinh `T` + số), lưu kết quả thuật toán vào `self.last_match_result: MatchResult`, đặt `self.last_failure = None` và trả về `Trip` (thao tác atomic: xác thực mọi điều kiện trước khi biến đổi dữ liệu).
    - `dispatch_all(strategy: MatchStrategy) -> list[Trip]`: Điều phối liên tục các yêu cầu trong hàng đợi cho đến khi hàng đợi rỗng hoặc không thể ghép thêm chuyến nào. Trả về danh sách các `Trip` được tạo.
    - `ride_estimate(request_id_or_pickup: str, dropoff_node: str | None = None) -> tuple[float, list[str]] | None`: Tính khoảng cách/thời gian và lộ trình di chuyển từ điểm đón đến điểm trả khách bằng thuật toán tìm đường ngắn nhất. Hỗ trợ 2 cách gọi: truyền `request_id` (tra cứu điểm đón/trả từ yêu cầu đã lưu) hoặc truyền trực tiếp cặp `(pickup_node, dropoff_node)`. Trả về `(quang_duong, danh_sach_dinh)` hoặc `None` nếu không có đường đi.
  - **Vòng đời tài xế, Hoàn thành & Hủy chuyến**:
    - `complete_trip(trip_id: str) -> bool`: Tìm chuyến đi tương ứng. Nếu không tồn tại hoặc `trip.status != ASSIGNED` thì trả về `False`. Ngược lại đổi `Trip.status` sang `COMPLETED`, gọi `driver.release()` để chuyển tài xế về `FREE`, cập nhật vị trí tài xế về `dropoff_node` của chuyến và trả về `True`.
    - `cancel_trip(trip_id: str) -> bool`: Hủy chuyến đã điều phối (`ASSIGNED`). Tìm chuyến đi; nếu không tồn tại hoặc `trip.status != ASSIGNED` thì trả về `False` và không thay đổi bất kỳ dữ liệu nào. Ngược lại: kiểm tra tài xế và yêu cầu tương ứng tồn tại trước khi cập nhật (nguyên tử); đổi `Trip.status = CANCELLED`; gọi `driver.release()` giải phóng tài xế về `FREE` tại vị trí hiện tại (không đổi `node`); đổi `request.status = CANCELLED` (theo quyết định D1=A: yêu cầu được lưu trong `all_requests`, KHÔNG quay lại hàng đợi `RequestQueue`); trả về `True`.
  - **API Snapshot an toàn cho UI** (trả về bản sao, UI không can thiệp trực tiếp biến nội bộ):
    - `queue_snapshot() -> list[RideRequest]`: Danh sách yêu cầu đang đợi theo thứ tự hàng đợi (chỉ gồm các yêu cầu có trạng thái `QUEUED`).
    - `trips_snapshot() -> list[Trip]`: Danh sách lịch sử các chuyến đi (`ASSIGNED`, `COMPLETED`, `CANCELLED`).
    - `drivers_snapshot() -> dict[str, Driver]`: Danh sách tài xế hiện có.
  - **Giao tiếp trạng thái với JsonStorage**:
    - `Dispatcher.from_state(state: dict) -> Dispatcher`: Khởi tạo instance từ dữ liệu đã nạp (chỉ đưa yêu cầu `QUEUED` vào `RequestQueue`; giữ yêu cầu `CANCELLED` trong `all_requests`).
    - `Dispatcher.export_state() -> dict`: Trích xuất toàn bộ dữ liệu đối tượng để lưu trữ (bao gồm cả `locations`, các `Trip` và `RideRequest` ở trạng thái `CANCELLED`).

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
  - `save_all(state: dict) -> None`: Nhận dict các đối tượng trên, chuyển đổi qua `to_dict()` và ghi an toàn xuống 4 file JSON trong `data/runtime/`. Chấp nhận và bảo toàn trạng thái `CANCELLED` của `Trip` và `RideRequest`.
- **Schema JSON (khóa gốc bắt buộc)**:
  - `graph.json`: `{"nodes": [{"id": "N1", "name": "Ngã tư A"}], "edges": [{"from": "N1", "to": "N2", "weight": 5.0}]}`
  - `drivers.json`: `{"drivers": [{"id": "D1", "name": "An", "node": "N1", "status": "free"}]}`
  - `requests.json`: `{"requests": [{"id": "R1", "pickup_node": "N3", "dropoff_node": "N7", "status": "queued"}]}`
  - `trips.json`: `{"trips": [{"id": "T1", "request_id": "R1", "driver_id": "D1", "eta": 7.0, "status": "assigned"}]}`
- **Kiểm tra tính nhất quán dữ liệu (Data Consistency Checks)**:
  - Tài xế bận (`BUSY`) phải có đúng một chuyến đang chạy (`ASSIGNED`).
  - Tài xế rảnh (`FREE`) không được có chuyến đang chạy (`ASSIGNED`).
  - Yêu cầu `ASSIGNED` phải gắn với một chuyến `ASSIGNED` tương ứng.
  - Yêu cầu `QUEUED` không được gắn với chuyến `ASSIGNED`.
  - Yêu cầu `CANCELLED` không được gắn với chuyến `ASSIGNED` hoặc `COMPLETED`.
  - Mọi vi phạm tính nhất quán ném `StorageError(Exception)` kèm thông báo tiếng Việt rõ ràng.
- **Quản lý ngoại lệ**:
  - Ném `StorageError(Exception)` kèm thông báo rõ ràng khi file JSON sai định dạng, thiếu khóa gốc hoặc có ID tham chiếu không tồn tại.
- **Kiểm thử**: Mọi unit test của storage phải sử dụng fixture `tmp_path` của pytest, không can thiệp vào `data/seed/`.

---

## 7. UI và Tích hợp ứng dụng (Thành viên 5 — Long)
- **Nguyên tắc**: UI chỉ tương tác qua API công khai của `Dispatcher` và `JsonStorage`. Tuyệt đối không chứa thuật toán Dijkstra hay thao tác trực tiếp với dữ liệu lưu trữ.
- **Kiến trúc Module giao diện (`src/ui/`)**:
  - `src/app.py`: Entrypoint mỏng cấu hình layout Streamlit và điều hướng radio thanh bên; chứa cơ chế bắt lỗi dữ liệu khởi động và hỗ trợ khôi phục tự động từ seed.
  - `src/ui/session.py`: Quản lý khởi tạo và lưu giữ instance `Dispatcher` và `JsonStorage` trong `st.session_state`.
  - `src/ui/tab_data.py`: Màn hình xem/thêm/sửa/xóa tài xế, xem đỉnh/cạnh đồ thị, tải lại dữ liệu từ đĩa.
  - `src/ui/tab_dispatch.py`: Màn hình tạo yêu cầu đặt xe, xem hàng đợi, chọn chiến lược từ `STRATEGIES`, nút điều phối từng chuyến/tất cả, hiển thị kết quả và giải thích lý do thất bại, danh sách lịch sử chuyến và nút hoàn thành/hủy chuyến (chuyến ASSIGNED có nút "Hủy chuyến" kèm xác nhận; chuyến CANCELLED hiện badge ⛔ Đã hủy và không có nút thao tác) kèm bản đồ lộ trình trực quan.
  - `src/ui/tab_benchmark.py`: Màn hình chạy thực nghiệm đối chuẩn A1 vs A2, hiển thị bảng và biểu đồ so sánh, kiểm thử độ mở rộng (scaling). *(Ngoại lệ: tab_benchmark được phép import trực tiếp `STRATEGIES` và `RoadGraph` để phục vụ đo đạc hiệu năng vi mô trên đồ thị ngẫu nhiên)*.
  - `src/ui/graph_view.py`: Sinh mã trực quan hóa mạng lưới đường bằng Graphviz DOT, tô màu trạng thái tài xế, điểm đón chờ, và làm nổi bật lộ trình đón/chở khách.
  - `src/ui/constants.py`: Import và tái xuất các hằng số trạng thái từ `models` để UI sử dụng thống nhất, tuyệt đối không hardcode chuỗi.
  - `src/ui/ports.py`: Protocol định nghĩa cổng giao tiếp trừu tượng `DispatcherPort` và `StoragePort`, quy định giao diện UI phụ thuộc (bao gồm `cancel_trip`).
  - `src/ui/mock.py`: Bộ mock Dispatcher và Storage chạy độc lập dùng `RoadGraph` và `STRATEGIES` thật để phục vụ kiểm thử nhanh UI mà không cần can thiệp file đĩa.
- **Bảo toàn trạng thái phiên làm việc**:
  - `Dispatcher` được khởi tạo một lần và lưu trong `st.session_state["dispatcher"]`.
  - Không nạp lại từ file ở mỗi lần Streamlit rerun để bảo toàn trạng thái điều phối đang chạy.
- **Tự động lưu trạng thái**:
  - UI gọi `save_all(dispatcher.export_state())` ngay sau mỗi thao tác thành công (thêm yêu cầu, hủy yêu cầu chờ, điều phối, hủy chuyến, đổi tài xế, hoàn thành chuyến).

---

## 8. Quy định Git, Phân quyền và Quy trình nhóm
- **Phân quyền sở hữu qua `.github/CODEOWNERS`**:
  - `src/models/` : `@Nhi`
  - `src/core/road_graph.py`, `src/core/strategies.py`, `tests/conftest.py` : `@Duy`
  - `src/core/dispatcher.py`, `src/core/structures.py` : `@Thong` (đã bỏ `src/core/undo_manager.py`)
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