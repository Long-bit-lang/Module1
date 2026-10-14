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
