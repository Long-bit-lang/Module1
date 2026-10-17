# Đề xuất thay đổi CONTRACT (cần nhóm thống nhất, mở PR riêng)

Phát hiện khi dựng UI (TV5) và đối chiếu `docs/CONTRACT.md` với kế hoạch phân công.
Chưa sửa trực tiếp vào CONTRACT vì thay đổi liên module phải được cả nhóm đồng ý.

| # | Vấn đề | Đề xuất | Người cần xác nhận | Trạng thái |
|---|---|---|---|---|
| 1 | `DispatchAction` ghi 3 trường trong kế hoạch nhưng 4 trường (`previous_driver_node`) trong CONTRACT; `dispatch_next` không đổi vị trí tài xế nên trường này chưa rõ mục đích. | Chốt một bản. Nếu không có lý do rõ ràng thì bỏ `previous_driver_node`. | Thông | Đang chờ chốt |
| 2 | Undo sau `complete_trip` làm sai trạng thái (tài xế đã rảnh và đã đổi vị trí, trip đã `COMPLETED`). | `complete_trip` xóa `undo_stack` và `redo_stack` (UI mock và Dispatcher thật đang làm theo cách này), `can_undo()` trả về `False` khi không còn action. | Thông | Đã triển khai |
| 3 | `save_all` cần `locations` nhưng `Dispatcher` không nhận hay giữ `locations`, nên `export_state()` không xuất được tên đỉnh cho `graph.json`. | Thêm `locations` vào constructor, `from_state` và `export_state`. | Thông, Thắng | Đã triển khai |
| 4 | `dispatch_next` chỉ trả `Trip` nên UI không có `visited_count`, `runtime_ms`, `path` để hiển thị; thiếu lý do thất bại. | Dispatcher bổ sung `last_match_result: MatchResult | None`, `last_failure: str | None`, `dispatch_all()`, `ride_estimate()`. | Thông, Duy | Đã triển khai |
| 5 | Bộ đếm ID R/D/T sau `from_state` chưa quy định (nguy cơ trùng ID); ID chuyến có dùng lại sau Undo hay không. | Khởi tạo bộ đếm từ ID lớn nhất đang có; không dùng lại ID đã cấp. | Thông | Đã triển khai |
| 6 | `visited_count` có tính các phần tử cũ (stale) trong heap hay chỉ đỉnh được chốt? | Chốt: đếm mọi lần pop khỏi min-heap, kể cả phần tử cũ/bản cũ (theo đúng định nghĩa CONTRACT §3), áp dụng cho cả A1 và A2. | Duy | Đã thống nhất |
| 7 | So sánh ETA của A1 và A2 bằng `==` có thể lệch do sai số số thực (hai thuật toán cộng theo hai chiều). | Test dùng `math.isclose`; hướng của `path` quy định từ tài xế đến điểm đón. | Duy | Đã thống nhất |
| 8 | `CODEOWNERS` gán `/docs/` cho `@Long` nên mọi sửa section của người khác đều cần Long duyệt. | Chấp nhận như vậy (Long là gác cổng tài liệu) và ghi rõ trong mục 5 của kế hoạch. | Cả nhóm | Đã thống nhất |

