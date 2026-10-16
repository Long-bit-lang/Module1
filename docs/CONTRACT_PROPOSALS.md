# Đề xuất thay đổi CONTRACT (cần nhóm thống nhất, mở PR riêng)

Phát hiện khi dựng UI (TV5) và đối chiếu `docs/CONTRACT.md` với kế hoạch phân công.
Chưa sửa trực tiếp vào CONTRACT vì thay đổi liên module phải được cả nhóm đồng ý.

| # | Vấn đề | Đề xuất | Người cần xác nhận |
|---|---|---|---|
| 1 | `DispatchAction` ghi 3 trường trong kế hoạch nhưng 4 trường (`previous_driver_node`) trong CONTRACT; `dispatch_next` không đổi vị trí tài xế nên trường này chưa rõ mục đích. | Chốt một bản. Nếu không có lý do rõ ràng thì bỏ `previous_driver_node`. | Thông |
| 2 | Undo sau `complete_trip` làm sai trạng thái (tài xế đã rảnh và đã đổi vị trí, trip đã `COMPLETED`). | `complete_trip` xóa `undo_stack` và `redo_stack` (UI mock đang làm theo cách này), hoặc `undo()` từ chối khi trip đã `COMPLETED`. | Thông |
| 3 | `save_all` cần `locations` nhưng `Dispatcher` không nhận hay giữ `locations`, nên `export_state()` không xuất được tên đỉnh cho `graph.json`. | Thêm `locations` vào constructor, `from_state` và `export_state`. | Thông, Thắng |
| 4 | `dispatch_next` chỉ trả `Trip` nên UI không có `visited_count`, `runtime_ms`, `path` để hiển thị. | Tạm thời UI bọc strategy (`RecordingStrategy`). Về lâu dài có thể thêm `Dispatcher.last_match: MatchResult \| None`. | Thông, Duy |
| 5 | Bộ đếm ID R/D/T sau `from_state` chưa quy định (nguy cơ trùng ID); ID chuyến có dùng lại sau Undo hay không. | Khởi tạo bộ đếm từ ID lớn nhất đang có; không dùng lại ID đã cấp. | Thông |
| 6 | `visited_count` có tính các phần tử cũ (stale) trong heap hay chỉ đỉnh được chốt? | Chốt: chỉ tính đỉnh được chốt lần đầu (bỏ qua bản cũ), áp dụng cho cả A1 và A2. | Duy |
| 7 | So sánh ETA của A1 và A2 bằng `==` có thể lệch do sai số số thực (hai thuật toán cộng theo hai chiều). | Test dùng `math.isclose`; hướng của `path` quy định từ tài xế đến điểm đón. | Duy |
| 8 | `CODEOWNERS` gán `/docs/` cho `@Long` nên mọi sửa section của người khác đều cần Long duyệt. | Chấp nhận như vậy (Long là gác cổng tài liệu) và ghi rõ trong mục 5 của kế hoạch. | Cả nhóm |
