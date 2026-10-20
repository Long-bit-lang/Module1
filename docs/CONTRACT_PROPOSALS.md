# Đề xuất thay đổi CONTRACT (cần nhóm thống nhất, mở PR riêng)

Phát hiện khi dựng UI (TV5) và đối chiếu `docs/CONTRACT.md` với kế hoạch phân công.
Chưa sửa trực tiếp vào CONTRACT vì thay đổi liên module phải được cả nhóm đồng ý.

| # | Vấn đề | Đề xuất | Người cần xác nhận | Trạng thái |
|---|---|---|---|---|
| 1 | `DispatchAction` ghi 3 trường trong kế hoạch nhưng 4 trường (`previous_driver_node`) trong CONTRACT; `dispatch_next` không đổi vị trí tài xế. | Thống nhất giữ lại trường này với mục đích phòng thủ (defensive programming), bảo đảm Undo luôn khôi phục vị trí chuẩn xác kể cả khi luồng nghiệp vụ tương lai mở rộng thay đổi vị trí tài xế lúc nhận chuyến. | Thông | Đã thống nhất |
| 2 | Undo sau `complete_trip` làm sai trạng thái (tài xế đã rảnh và đã đổi vị trí, trip đã `COMPLETED`). | `complete_trip` xóa `undo_stack` và `redo_stack` (UI mock và Dispatcher thật đang làm theo cách này), `can_undo()` trả về `False` khi không còn action. | Thông | Đã triển khai |
| 3 | `save_all` cần `locations` nhưng `Dispatcher` không nhận hay giữ `locations`, nên `export_state()` không xuất được tên đỉnh cho `graph.json`. | Thêm `locations` vào constructor, `from_state` và `export_state`. | Thông, Thắng | Đã triển khai |
| 4 | `dispatch_next` chỉ trả `Trip` nên UI không có `visited_count`, `runtime_ms`, `path` để hiển thị; thiếu lý do thất bại. | Dispatcher bổ sung `last_match_result: MatchResult | None`, `last_failure: str | None`, `dispatch_all()`, `ride_estimate()`. | Thông, Duy | Đã triển khai |
| 5 | Bộ đếm ID R/D/T sau `from_state` chưa quy định (nguy cơ trùng ID); ID chuyến có dùng lại sau Undo hay không. | Khởi tạo bộ đếm từ ID lớn nhất đang có; không dùng lại ID đã cấp. | Thông | Đã triển khai |
| 6 | `visited_count` có tính các phần tử cũ (stale) trong heap hay chỉ đỉnh được chốt? | Chốt: đếm mọi lần pop khỏi min-heap, kể cả phần tử cũ/bản cũ (theo đúng định nghĩa CONTRACT §3), áp dụng cho cả A1 và A2. | Duy | Đã thống nhất |
| 7 | So sánh ETA của A1 và A2 bằng `==` có thể lệch do sai số số thực (hai thuật toán cộng theo hai chiều). | Test với trọng số nguyên dùng so sánh `==` là chính xác; bổ sung test riêng cho trọng số float dùng `math.isclose`; hướng của `path` quy định từ tài xế đến điểm đón. | Duy | Đã thống nhất |
| 8 | `CODEOWNERS` gán `/docs/` cho `@Long` nên mọi sửa section của người khác đều cần Long duyệt. | Chấp nhận như vậy (Long là gác cổng tài liệu) và ghi rõ trong mục 5 của kế hoạch. | Cả nhóm | Đã thống nhất |
| 9 | Thiếu phương thức hủy yêu cầu đang chờ (`QUEUED`) khi khách hàng đổi ý. | Bổ sung `Dispatcher.cancel_request(request_id: str) -> bool` xóa yêu cầu khỏi hàng đợi và danh sách `all_requests`. | Thông, TV5 | Đã triển khai |
| 10 | Hàng đợi `RequestQueue` chỉ hỗ trợ `enqueue`, `dequeue`, `requeue_head`, thiếu xóa phần tử ở vị trí bất kỳ. | Bổ sung `RequestQueue.remove(request_id: str) -> bool`, cập nhật chuẩn xác con trỏ `_head`, `_tail` và `_size`. | Thông | Đã triển khai |
| 11 | `Stack` và `RequestQueue` thiếu phương thức duyệt và xem trước đỉnh mà không làm thay đổi cấu trúc dữ liệu. | Bổ sung `Stack.peek()`, `Stack.__iter__()`, `RequestQueue.peek()`, `RequestQueue.__iter__()`. | Thông, Duy | Đã triển khai |
| 12 | CONTRACT §3 ghi `reversed()` trả về "một RoadGraph mới", nhưng code có cơ chế cache `_reversed_cache`. | Làm rõ trong tài liệu: `reversed()` trả về đồ thị đảo được cache để tái sử dụng, tự vô hiệu hóa (invalidation) khi có thay đổi cấu trúc (`add_node`/`add_edge`). | Duy | Đã thống nhất |
| 13 | Thực thể `Trip` và `RideRequest` hiện chưa có trường thời gian tạo (`created_at`), khiến UI không thể hỗ trợ lọc lịch sử chuyến theo mốc thời gian thực. | Đề xuất bổ sung trường `created_at: float | str` (mặc định `time.time()` hoặc ISO-8601 string) vào `Trip` và `RideRequest`, hỗ trợ tương thích ngược trong `to_dict()`/`from_dict()` (nếu file JSON cũ thiếu thì gán giá trị mặc định). | Thông, Duy, TV5 | Đang đề xuất (chưa sửa model) |


