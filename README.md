# Hệ thống Quản lý và Điều phối Đặt xe Thông minh trên Đồ thị Giao thông

Python · Streamlit · JSON · Git · uv

Ứng dụng mô phỏng điều phối đặt xe trên đồ thị giao thông có hướng (trọng số = phút di chuyển).
Mỗi yêu cầu đặt xe được ghép với tài xế rảnh có ETA nhỏ nhất bằng một trong hai thuật toán:
**A1** (Dijkstra từ từng tài xế) và **A2** (Dijkstra trên đồ thị đảo chiều từ điểm đón).
Hỗ trợ hàng đợi FIFO, Undo/Redo thao tác điều phối, hoàn thành chuyến và lưu dữ liệu JSON.

## Cài đặt
Yêu cầu: [uv](https://docs.astral.sh/uv/) và Python 3.12.
```bash
uv sync
```

## Chạy ứng dụng
```bash
uv run streamlit run src/app.py
```
Thanh bên của ứng dụng cho biết đang chạy **backend thật** hay **backend giả lập (mock)**.
Mock chỉ được dùng khi `Dispatcher` / `JsonStorage` / `STRATEGIES` thật chưa đủ API theo
`docs/CONTRACT.md`; có thể ép bằng biến môi trường:
```bash
RIDE_DISPATCH_BACKEND=mock uv run streamlit run src/app.py   # luôn dùng mock
RIDE_DISPATCH_BACKEND=real uv run streamlit run src/app.py   # bắt buộc dùng bản thật, lỗi nếu thiếu
```
(Windows PowerShell: `$env:RIDE_DISPATCH_BACKEND="mock"` trước khi chạy.)

## Chạy kiểm thử
```bash
uv run pytest
```
`tests/test_contract_api.py` kiểm tra API thật có khớp CONTRACT chưa (các mục chưa xong được
đánh dấu `xfail`, người phụ trách module gỡ dấu này khi hoàn thành).

## Kịch bản demo 5 bước
1. **Tab "Quản lý dữ liệu"**: xem danh sách tài xế và đồ thị; thêm một tài xế mới tại một đỉnh bất kỳ.
2. **Tab "Điều phối chuyến"**: tạo 2–3 yêu cầu đặt xe; quan sát hàng đợi FIFO.
3. Chọn thuật toán **A1**, bấm *Điều phối*: xem tài xế được chọn, ETA, số đỉnh đã thăm, thời gian chạy và lộ trình.
4. Bấm **Undo** (yêu cầu quay về đầu hàng, tài xế rảnh trở lại), rồi **Redo**; điều phối lại bằng **A2** và so sánh kết quả.
5. Bấm **Hoàn thành chuyến** để giải phóng tài xế, rồi sang tab **"Đối chuẩn thuật toán"**
   để chạy A1 vs A2 và xem bảng/biểu đồ số đỉnh đã thăm và runtime.

Lưu ý: Undo/Redo giữ qua các lần rerun của Streamlit nhưng **mất khi tải lại trang (F5)** hoặc bấm
"Tải lại dữ liệu từ đĩa", vì lịch sử không được lưu xuống JSON. Hoàn thành chuyến sẽ xóa lịch sử Undo/Redo.

## Cấu trúc
| Thư mục | Phụ trách | Nội dung |
|---|---|---|
| `src/models/` | TV1 | BaseEntity, Location, Driver, RideRequest, Trip, hằng số trạng thái |
| `src/core/road_graph.py`, `strategies.py` | TV2 | RoadGraph, Dijkstra A1/A2, `STRATEGIES` |
| `src/core/dispatcher.py`, `structures.py`, `undo_manager.py` | TV3 | Điều phối, hàng đợi FIFO, Undo/Redo |
| `src/core/json_storage.py`, `data/seed/` | TV4 | Đọc/ghi JSON atomic, dữ liệu mẫu (`data/runtime/` do app tự sinh, không commit) |
| `src/app.py`, `src/ui/`, `docs/`, README | TV5 | Giao diện Streamlit, tích hợp, tài liệu |

Giao diện (`src/ui/`): `session.py` (Dispatcher/JsonStorage trong `st.session_state`, tự lưu),
`tab_data.py`, `tab_dispatch.py`, `tab_benchmark.py`, `ports.py` (Protocol theo CONTRACT),
`mock.py` (backend giả lập), `constants.py` (hằng số trạng thái).

Hợp đồng giữa các module: xem `docs/CONTRACT.md`. Đề xuất thay đổi đang chờ nhóm duyệt: `docs/CONTRACT_PROPOSALS.md`.

## Quy trình Git
Mỗi người một nhánh (`feat/models`, `feat/algorithms`, `feat/dispatcher`, `feat/storage`, `feat/ui`),
không commit trực tiếp lên `main`, mọi thay đổi qua Pull Request có approve của chủ sở hữu thư mục
(theo `.github/CODEOWNERS`). Tiền tố commit: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`.
`pyproject.toml` và `uv.lock` do TV5 (Long) quản lý; cần thêm thư viện hãy báo Long.
