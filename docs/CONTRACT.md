# Hợp đồng giao tiếp giữa các module

> Thay đổi chữ ký hàm hoặc schema JSON phải báo cả nhóm và cập nhật file này.

## Models (TV1)
- Mọi entity kế thừa `BaseEntity`: có `id` ổn định, `to_dict()` và `from_dict(data)`.
- `Driver.status`: `"free"` | `"busy"`; đổi trạng thái qua `assign()` / `release()`.
- `RideRequest`: `id`, `pickup_node`, `dropoff_node`.
- `Trip`: `id`, `request_id`, `driver_id`, `eta`, `status`.

## RoadGraph (TV2)
- `add_edge(u, v, weight)`, `nodes()`, `neighbors(u) -> list[(v, w)]`, `reversed() -> RoadGraph`.

## MatchStrategy (TV2)
- `find_driver(graph, pickup_node, free_drivers: dict[driver_id, node]) -> MatchResult`
- `MatchResult`: `driver_id | None`, `eta | None`, `visited_count`, `path | None`, `runtime_ms`.

## Dispatcher (TV3)
- Không đọc/ghi file trực tiếp.
- `submit_request(request)`, `dispatch_next(strategy) -> Trip | None`, `undo()`, `redo()`.
- Khi không có tài xế / không có đường đi: không tạo Trip, yêu cầu vẫn ở đầu hàng đợi.

## JsonStorage (TV4)
- `load_all() -> dict`, `save_all(state: dict)`; ghi qua file tạm rồi thay thế.
- Lỗi file hỏng/thiếu trường -> `StorageError` với thông báo dễ hiểu.
- File: `data/graph.json`, `drivers.json`, `requests.json`, `trips.json`.

## UI (TV5)
- Chỉ gọi Dispatcher / JsonStorage; không chứa Dijkstra hay logic Undo/Redo.




---

# Quy ước bổ sung (chốt ở Ngày 2)

## 1. ID và đơn vị
- Mọi ID là chuỗi (`str`) và không bao giờ đổi sau khi tạo.
- ID đỉnh: `N1`, `N2`, ... · tài xế: `D1`, `D2`, ... · yêu cầu: `R1`, ... · chuyến: `T1`, ...
- Dispatcher sinh ID mới theo bộ đếm lớn nhất hiện có + 1, ví dụ `R` + số.
- Trọng số cạnh và ETA tính bằng **phút**, kiểu `float`, `>= 0`.
- ETA không đến được: `None` (không dùng `inf` để tránh lỗi khi ghi JSON).

## 2. Schema JSON (thư mục `data/`)

`graph.json`
```json
{
  "nodes": [{"id": "N1", "name": "Ngã tư A"}],
  "edges": [{"from": "N1", "to": "N2", "weight": 5}]
}
```
Đồ thị có hướng; cạnh hai chiều được ghi thành 2 cạnh riêng.

`drivers.json`
```json
{"drivers": [{"id": "D1", "name": "An", "node": "N1", "status": "free"}]}
```

`requests.json` (thứ tự mảng chính là thứ tự hàng đợi FIFO)
```json
{"requests": [{"id": "R1", "pickup_node": "N3", "dropoff_node": "N7", "status": "queued"}]}
```

`trips.json` (lịch sử chuyến)
```json
{"trips": [{"id": "T1", "request_id": "R1", "driver_id": "D1", "eta": 7.0, "status": "assigned"}]}
```

Tất cả file đều có khóa gốc như trên, kể cả khi rỗng (`{"drivers": []}`).
Mọi `node`, `pickup_node`, `driver_id`, `request_id` phải tham chiếu tới ID có thật.

## 3. Trạng thái
- `Driver.status`: `"free"` | `"busy"`
- `RideRequest.status`: `"queued"` | `"assigned"`
- `Trip.status`: `"assigned"` | `"completed"` (nếu nhóm có làm hoàn thành chuyến)
- Điều phối thành công: request thành `assigned`, driver thành `busy`, thêm 1 Trip.
- Undo một lần điều phối: xóa Trip đó, driver về `free`, request về `queued` **ở đầu hàng đợi**.
- Hàng đợi chỉ chứa request `queued`.

## 4. Luật chọn tài xế khi hòa ETA
- Chọn ETA nhỏ nhất; nếu hòa thì chọn `driver_id` nhỏ nhất theo so sánh chuỗi.
- Cả A1 và A2 đều phải theo luật này, nếu không test đối chiếu sẽ lệch.
- Lưu ý cho A2: không dừng ngay ở tài xế đầu tiên lấy ra khỏi heap. Phải xét tiếp mọi tài xế có cùng khoảng cách nhỏ nhất rồi mới áp luật hòa. Thứ tự trong heap dùng `(dist, node_id)`.
- Nhiều tài xế đứng cùng một đỉnh: cũng áp luật hòa này.

## 5. Dữ liệu trả về và lỗi
- `MatchResult.driver_id = None` và `eta = None` khi: không có tài xế rảnh, hoặc không tài xế nào đến được điểm đón. `visited_count` vẫn được điền.
- Điểm đón không có trong đồ thị: `RoadGraph` / Dispatcher ném `ValueError` với thông báo rõ ràng. UI bắt lỗi này và hiển thị cho người dùng.
- Dữ liệu sai định dạng: `JsonStorage` ném `StorageError` (đã có trong `json_storage.py`).

## 6. Trạng thái toàn hệ thống và lưu dữ liệu
- `JsonStorage.load_all()` trả về dict các **đối tượng** (không phải dict thô):
```python
{
  "graph": RoadGraph,
  "drivers": {driver_id: Driver},
  "requests": [RideRequest],   # theo thứ tự hàng đợi
  "trips": [Trip],
}
```
- `JsonStorage.save_all(state)` nhận đúng cấu trúc trên. Việc chuyển sang dict (`to_dict`) và ngược lại (`from_dict`) do JsonStorage gọi.
- Dispatcher có thêm:
  - `Dispatcher.from_state(state)` để khởi tạo từ dữ liệu đã nạp.
  - `Dispatcher.export_state() -> dict` để lấy dữ liệu cần lưu.
- **UI (TV5) gọi `save_all(dispatcher.export_state())` sau mỗi thao tác thành công**: thêm request, điều phối, Undo, Redo, thay đổi tài xế.
- Lịch sử Undo/Redo **không** được lưu; mở lại ứng dụng thì hai ngăn xếp rỗng.
- Lần chạy đầu: nếu thiếu file trong `data/`, JsonStorage tạo dữ liệu mẫu rồi báo lại cho UI.

## 7. Quy ước chung
- Models không import từ `core/`; `core/` chỉ import từ `models/`; UI import cả hai.
- Chỉ UI mới được dùng `streamlit`.
- Import theo kiểu `from models.driver import Driver`, `from core.dispatcher import Dispatcher` (không có tiền tố `src.`).
- Thay đổi bất kỳ mục nào ở trên: báo nhóm, sửa file này và thông báo trong Pull Request.